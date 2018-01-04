# Auxiliary script for running git-persistence on a full repository.
# This is highly customized and it is meant to used as a demo example for uses of git_persistence.py
# The script utilizes also git fame for comparisons. If you want to avoid having to use git fame either remove it
# from the code below or store_each_revision=False

import os
import csv
import re
from git_persistence import GitPersistence
import parallel_lib
import sys
import datetime
import subprocess

# Getting the git repo dir from argv
GIT_PATH = sys.argv[1]

# Excluding files that are binary
FILES_TO_EXCLUDE = ["png", "bmp", "dll", "jpg", "jpeg", "exe", "ttf", "ico", "icns", "svg", "ogg"]


def execute_and_return(command_list, git_path):
    """ Helper function that runs a command and stores output as a file

    :param command_list: list containing command with all parameters
    :type command_list: list
    :param git_path: working directory path of git repo
    :type git_path: str

    :return: output and error (if any)
    :rtype: tuple
    """
    os.chdir(git_path)
    process = subprocess.Popen(command_list,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, err = process.communicate()
    os.chdir("../")
    return out, err


def read_git_commit_log(data):
    """ Returns commit log from a file containing the exported git log.
    Note: Highly customized for a specific purpose.

    :param data: specific format list of commits returned by git log:
     --pretty*=format:@%H%n%an%n%ae%n%at%n%cn%n%ce%n%ct@
    :type data: str

    :return: list of formatted entries
    :rtype: list
    """
    matches = re.findall('@(.*?)\n(.*?)\n(.*?)\n(.*?)\n(.*?)\n(.*?)\n(.*?)@\n(.*?)(?:$|\n)', data, re.DOTALL)
    return matches


def store_revisions(commit_list, file_referenced, filename):
    """ Append commit log info to a tab separated file

    :param commit_list: list containing git log info
    :type commit_list: list
    :param file_referenced: filename that git log points to
    :type file_referenced: str
    :param filename: filename that git log is appened in
    :type filename: str

    :return: None
    :rtype: None
    """
    f = open(filename, 'a')
    for commit in commit_list:
        text = "\t".join(commit)
        text += "\t" + file_referenced
        f.write(text + "\n")
    f.close()


def reset_files():
    """ Resets files relevant to the output that will be stored by this script

    :return: None
    :rtype: None
    """
    if os.path.isfile("commits.tsv"):
        os.remove("commits.tsv")
    if os.path.isfile("persistence_scores.tsv"):
        os.remove("persistence_scores.tsv")
    if os.path.isfile("times.tsv"):
        os.remove("times.tsv")
    if os.path.isfile("pa_per_rev.tsv"):
        os.remove("pa_per_rev.tsv")
    if os.path.isfile("git_fame_per_rev.tsv"):
        os.remove("git_fame_per_rev.tsv")


def pre_process():
    """ Obtain all files that are part of the repo and expected to be processed

    :return: files to be processed by script
    :rtype: list
    """
    out, err = execute_and_return(["git", "ls-tree", "--full-tree", "-r", "HEAD"], GIT_PATH)
    files = []
    csv_reader_descriptor = csv.reader(out.decode("utf-8").splitlines(),
                                       delimiter='\t', quotechar=None, escapechar=None)
    for row in csv_reader_descriptor:
        files.append(row[1])
    return files


def process_git_file(filename, store_each_revision=True):
    """ Calculate git-persistence scores for a file in a git repository. Store results in pre-specified files.

    :param filename: filename to be parsed by git-persistence
    :type filename: str
    :param store_each_revision: store git-persistence results for every revision made to the file
    :type store_each_revision: bool

    :return: None
    :rtype: None
    """
    parallel_lib.mark_time()
    print(filename + " " + filename.split(".")[len(filename.split(".")) - 1])
    if filename.split(".")[len(filename.split(".")) - 1] not in FILES_TO_EXCLUDE:
        current_file = filename
        print(current_file)
        data_ag = 0
        out, err = execute_and_return(["git", "log", "--name-only",
                                       "--pretty=format:@%H%n%an%n%ae%n%at%n%cn%n%ce%n%ct@", "--follow",
                                       current_file], GIT_PATH)
        # Commit list always returned in chronological order by git
        commit_list = read_git_commit_log(out.decode("utf-8"))
        # Storing all revisions for records, this is the same commit log appearing on github
        store_revisions(commit_list, current_file, "commits.tsv")
        i = 0
        git_fame_processed_commits = []  # auxiliary list so that we won't obtain git fame for the same commit
        for commit in reversed(commit_list):
            aggregate_username = commit[1]
            aggregate_username = aggregate_username.encode("utf-8")
            out, err = execute_and_return(["git", "show", commit[0] + ":" + commit[7]], GIT_PATH)
            try:
                data = out.decode("utf-8")
            except UnicodeEncodeError:  # Try alternative encoding just in case otherwise it is a binary file probably
                data = out.decode("utf-16")
            data_ag += len(data.splitlines(False))

            # Start new tracking or update existing (depending on whether we look at the same file)
            if i == 0:
                tracking = GitPersistence(data, aggregate_username)
            else:
                tracking.update(data, aggregate_username)

            # Store current revision info
            if store_each_revision:
                results = tracking.calculate_ownership()
                f = open("pa_per_rev.tsv", "a")
                users = [w for w in results[0].keys()]
                users.extend([w for w in results[1].keys()])
                for result in set(users):
                    f.write("%s\t%s\t%s\t%s\t%s\n" %
                            (commit[0],
                             current_file,
                             result.decode("utf-8"),
                             str(results[0].get(result, 0)),
                             str(results[1].get(result, 0))))
                f.close()
                
                # Get additional git-fame (blame) stats per revision (there is a limitation on the basis of date)
                # git-fame uses always the latest commit for that date
                # The solution below produces duplicates that need to be removed during the analysis (fairly easy)
                if commit[0] not in git_fame_processed_commits:
                    out, err = execute_and_return(["git", "fame", "--format=csv", "--timeout=-1", "-h", "--before",
                                                   datetime.datetime.fromtimestamp(int(commit[3])).
                                                  strftime('%Y-%m-%d')],
                                                  GIT_PATH)
                    f = open("git_fame_per_rev.tsv", "a")
                    git_fame_lines = out.decode("utf-8").splitlines()
                    a = 0
                    for line in git_fame_lines:
                        if a != 0:  # skip first line
                            f.write("%s,%s\n" % (line.strip(), commit[0]))
                        a += 1
                    f.close()
                    git_fame_processed_commits.append(commit[0])

            i += 1
        results = tracking.calculate_ownership()
        f = open("persistence_scores.tsv", "a")

        # If you need to see changes as a diff file in html activate this
        # This is an expensive operation so restrict it somehow
        # with open("diff.html", "w") as text_file:
        #    text_file.write(tracking.html_print())

        # Aggregate users into a list that you can loop
        # this eliminates missing on some that had one value but not another
        users = [w for w in results[0].keys()]
        users.extend([w for w in results[1].keys()])
        for result in set(users):
            f.write("%s\t%s\t%s\t%s\n" %
                    (current_file,
                     result.decode("utf-8"),
                     str(results[0].get(result, 0)),
                     str(results[1].get(result, 0))
                     ))
        f.close()
        execution_time = parallel_lib.mark_time(True)
        with open("times.tsv", "a") as file_descriptor:
            file_descriptor.write("%s\t%s\t%s\n" %
                                  (current_file,
                                   str(round(data_ag / len(commit_list), 2)),
                                   str(execution_time)))


# Plenty of commented lines used for different functions and tests
# Some are deprecated or will be included in the last version
# As it stands the script below utilizes 1 core (value can be changed)
# and applies PCC to scientist repository    
if __name__ == '__main__':
    FILES = pre_process()
    reset_files()
    parallel_lib.parallel_process(8, FILES, process_git_file)
