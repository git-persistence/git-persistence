# Auxiliary script for running git-persistence on a full repository.
# This is highly customized and it is meant to used as a demo example for uses of git_persistence.py

from subprocess import call
import os
import csv
import re
from git_persistence import GitPersistence
import parallel_lib
import sys

# Getting the git repo dir from argv
GIT_PATH = sys.argv[1]

# Excluding files that are binary
FILES_TO_EXCLUDE = ["png", "bmp", "dll", "jpg", "jpeg", "exe", "ttf", "ico", "icns", "svg", "ogg"]


def execute_and_save(command_list, filename, git_path):
    """ Helper function that runs a command and stores output as a file

    :param command_list: list containing command with all parameters
    :type command_list: list
    :param filename: filename to store output in
    :type filename: str
    :param git_path: working directory path of git repo
    :type git_path: str

    :return: None
    :rtype: None
    """
    f = open(filename, "w")
    os.chdir(git_path)
    call(command_list, stdout=f)
    os.chdir("../")
    f.close()


def read_git_commit_log(filename):
    """ Returns commit log from a file containing the exported git log.
    Note: Highly customized for a specific purpose.

    :param filename: filename that contain git log info. Format is expected to be:
     --pretty*=format:@%H%n%an%n%ae%n%at%n%cn%n%ce%n%ct@
    :type filename: str

    :return: list of formatted entries
    :rtype: list
    """
    with open(filename, 'r') as file_descriptor:
        data = file_descriptor.read()
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


def pre_process():
    """ Obtain all files that are part of the repo and expected to be processed

    :return: files to be processed by script
    :rtype: list
    """
    execute_and_save(["git", "ls-tree", "--full-tree", "-r", "HEAD"], "files.tmp", GIT_PATH)
    files = []
    with open('files.tmp', 'rt') as csv_file:
        csv_reader_descriptor = csv.reader(csv_file, delimiter='\t', quotechar=None, escapechar=None)
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
        hash_name = hashlib.md5(current_file.encode('utf-8')).hexdigest()
        execute_and_save(["git", "log", "--name-only",
                          "--pretty=format:@%H%n%an%n%ae%n%at%n%cn%n%ce%n%ct@", "--follow",
                          current_file],
                         "commits" + hash_name + ".tmp", GIT_PATH)
        # Commit list always returned in chronological order by git
        commit_list = read_git_commit_log("commits" + hash_name + ".tmp")
        # Storing all revisions for records, this is the same commit log appearing on github
        store_revisions(commit_list, current_file, "commits.tsv")
        i = 0
        for commit in reversed(commit_list):
            aggregate_username = commit[1]
            aggregate_username = aggregate_username.encode("utf-8")
            execute_and_save(["git", "show", commit[0] + ":" + commit[7]], hash_name, GIT_PATH)
            try:
                with open(hash_name, 'r', encoding="utf-8") as my_file:
                    data = my_file.read()
            except UnicodeEncodeError:  # Try alternative encoding just in case otherwise it is a binary file probably
                with open(hash_name, 'r', encoding="utf-16") as my_file:
                    data = my_file.read()
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
            i += 1
            os.remove(hash_name)
        os.remove("commits" + hash_name + ".tmp")
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
    files = pre_process()
    reset_files()
    parallel_lib.parallel_process(32, files, process_git_file)
