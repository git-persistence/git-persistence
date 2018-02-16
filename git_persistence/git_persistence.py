import difflib
from difflib import Match
import hashlib
import random
import math
from collections import Counter


class GitPersistence:
    """Tracks commit code ownership through different updates
    Name for package is git-persistence, however th class in Python is named as such to comply with PEP8 specs
    """
    code = []
    code_text = ""
    commit_no = 0

    new_code = []
    new_code_text = ""
    new_commit_no = 0

    user_index = dict()

    def __init__(self, rev, user):
        """ Initializes the class by receiving the first state of code

        :param rev: string containing code
        :type rev: str
        :param user: user that has submitted the first code
        :type user: bytes

        :return: None
        :rtype: None
        """
        self.__pre_process_revision(rev, user)
        self.__insert_commits(0, len(rev), self.new_commit_no)
        self.__commit()

    def __pre_process_revision(self, rev, user):
        """ Initialize variables

        :param rev: string containing code
        :type rev: str
        :param user: user that has submitted the first code
        :type user: bytes

        :return: None
        :rtype: None
        """
        self.new_code_text = rev
        self.new_commit_no = self.commit_no + 1
        self.new_code = []
        self.user_index[self.new_commit_no] = user

    def __commit(self):
        """ Commits changes from new to current variables, variable switching

        :return: None
        :rtype: None
        """
        self.code = self.new_code
        self.code_text = self.new_code_text
        self.commit_no = self.new_commit_no

    def __insert_commits(self, start, stop, number):
        """ Insert in list 'numbers' that have a value based on the revision

        :param start: almost always zero
        :type start: int
        :param stop: end range for a for loop
        :type stop: int
        :param number: the numeric value of the commit that submitted the new revision (increments with every update())
        :type number: int

        :return: None
        :rtype: None
        """
        for x in range(start, stop):
            self.new_code.append(number)

    def __add_match_blocks(self, a, length):  #
        """ Apply existing numeric value to each character based on the previous code's matched block

        :param a: start position on old revision
        :type a: int
        :param length: length of matched character block
        :type length: int

        :return: None
        :rtype: None
        """
        for x in range(0, length):
            self.new_code.append(self.code[x + a])

    def __calculate_blocks(self, rev, min_threshold=0.6):
        """ Calculate line by line, which lines have changed based on min_threshold and then
        check for within line changes (char by char) and return which a list of matched code blocks
        that have remained the same.

        :param rev: text of new revision
        :type rev: str
        :param min_threshold: a percentage of similarity for line by line comparisons
        :type min_threshold: float bound between 0.0 to 1.0

        :return: matched code blocks that have remained the same, list of tuples
        :rtype: list [(start position in original text, start pos in new text, length),(),()...]
        """
        matches = []  # contains tuples of matched parts
        original = self.code_text.splitlines(True)  # original text with split lines (retains \n as a char)
        new = rev.splitlines(True)  # the new submitted text
        found = True

        # Calculate start positions for each line in original strings
        char_start_original = []
        char_start_new = []
        additive = 0
        for x in range(0, len(original)):
            char_start_original.append(additive)
            additive += len(original[x])
        additive = 0
        for y in range(0, len(new)):
            char_start_new.append(additive)
            additive += len(new[y])

        # Match identification code below
        # worst-case: O(x*y) or O(x^2) if x and y equal length and changes existing in all lines
        # best-case: O(x)

        # Constructing a hash-multiset to speed the process later on
        cnt = Counter()
        for word in new:
            cnt[word] += 1

        diffs = []
        new_tmp = new  # Temporary object that we modify on the fly, used for reference
        y_list = list(range(0, len(new)))  # Temporary object for dynamic recursion
        counter = 0
        for x in range(0, len(original)):
            diffs.append([])
            if cnt[original[x]] > 0:  # it exists (this is O(1) which helps skip a lot of comparisons)
                y = y_list.index(new_tmp.index(original[x]))  # reference index number in y_list (iterable)
                # Adding a matched record that simulates what difflib would find if it were to compare the two strings
                # Basically the whole new line matches the old, difflib always has a zero size match as the last
                # element.
                diffs[x].append([x, y_list[y], 1.0,
                                 [Match(a=0, b=0, size=len(original[x])),
                                  Match(a=len(original[x]), b=len(original[x]), size=0)]
                                 ])
                del (y_list[y])  # delete the existing object's line
                # This is like deleting the record for the purposes of retrieving the index from the tmp object.
                # Deleting would have shifted the numbers
                new_tmp[new_tmp.index(original[x])] = 0
                cnt[original[x]] -= 1  # decrement
            else:  # no duplicate so we have to compare the item with the rest of the list (code modified or removed)
                for y in range(0, len(y_list)):
                    counter += 1
                    line_diff_result = difflib.SequenceMatcher(None, original[x], new[y_list[y]], autojunk=False)
                    # Sanity check below, the hash-multiset should have removed all identical lines
                    if line_diff_result.ratio() == 1:
                        diffs[x].append([x, y_list[y], line_diff_result.ratio(),
                                         line_diff_result.get_matching_blocks()])
                        del (y_list[y])
                        break
                    else:
                        diffs[x].append([x, y_list[y], line_diff_result.ratio(),
                                         line_diff_result.get_matching_blocks()])
        print(
            "Total comparisons: " + str(counter))  # For visually seeing whether the optimizations work and we avoid n^2
        del cnt
        del new_tmp

        # Iterate through all the calculated diffs and figure out the best matches
        # The look keeps going on and on until all possible matches are found (could be rewritten as a recursive func)
        # to_delete serves a deleting agent so that after a match is appended, the lines found to match are eliminated
        # from further consideration
        to_delete = -999  # init a non-sense number
        while found is True:
            found = False
            max_match = [0, 0, 0, 0]  # This will hold the best match between line_x and line_y
            for x in range(0, len(diffs)):
                for y in range(0, len(diffs[x])):
                    if diffs[x][y][1] == to_delete:
                        diffs[x][y] = [0, 0, 0, 0]
                    else:
                        if diffs[x][y][2] > min_threshold and max_match[2] < diffs[x][y][2]:
                            max_match = [diffs[x][y][0], diffs[x][y][1], diffs[x][y][2], diffs[x][y][3], x]
            if max_match[2] != 0:  # we found a line that looks similar enough and was likely moved
                found = True
                for m in max_match[3]:
                    if m[2] != 0:  # make sure that the matched content matches at least 1 char (sanity check)
                        matches.append([char_start_original[max_match[0]] + m[0],
                                        char_start_new[max_match[1]] + m[1],
                                        m[2]])
                del (diffs[max_match[4]])
                to_delete = max_match[1]
        return matches

    def update(self, rev, user):
        """Update old code with new code revision and update which revision is character came from

        :param rev: text of new revision
        :type rev: str
        :param user: user that submitted the new revision
        :type user: bytes

        :return: None
        :rtype: None
        """
        self.__pre_process_revision(rev, user)

        # Code using similarity metric line by line and using LCS within line (difflib)
        matches = self.__calculate_blocks(rev)

        pointer = 0
        matches = sorted(matches, key=lambda l: l[1])
        for code_block_match in matches:
            # Anything before our pointer in matched block is new code, otherwise it must be existing code
            if code_block_match[1] != pointer and code_block_match[1] < len(self.new_code_text):
                self.__insert_commits(0, code_block_match[1] - pointer, self.new_commit_no)
                pointer += code_block_match[1] - pointer  # Shift pointer based on characters added
            self.__add_match_blocks(code_block_match[0], code_block_match[2])
            pointer += code_block_match[2]  # Shift pointer by n number of chars from the matched code block
        # If there was unmatched new code at the end after all code block matches, then it must be new code
        if len(self.new_code_text) > len(self.new_code):
            self.__insert_commits(0, len(self.new_code_text) - len(self.new_code), self.new_commit_no)
        self.__commit()

    def calculate_ownership(self, log_base=10):
        """Calculate ownership summarized statistics for the last commit

        :param log_base: base for logarithm that helps curve the influence of older commits
        :type log_base: int

        :return: [sums, avg_persistence] Returns a tuple containing dictionaries with key = user_id
        All results are based on the last iteration submitted (last update() called)
        sum_persistence: add all persistence scores for each character that belong to a user_id
        avg_persistence: provides the mean persistence score for each character that belong to a user_id
        :rtype: list [dict(), dict()]
        """
        aggregate = dict()
        counts = dict()
        sums_persistence = dict()
        persistence = [self.commit_no + 1 - x for x in self.code]  # inverting scores to get persistence
        avg_persistence = dict()
        i = 0  # auxiliary counter
        for x in self.code:  # self.code and persistence are exactly the same length
            if counts.get(x, 0) == 0:
                counts[x] = 1
            else:
                counts[x] += 1
            if aggregate.get(x, 0) == 0:
                aggregate[x] = persistence[i]
            else:
                aggregate[x] += persistence[i]
            i += 1
        for x in counts:
            if sums_persistence.get(self.user_index[x], 0) == 0:
                sums_persistence[self.user_index[x]] = counts[x]
                avg_persistence[self.user_index[x]] = aggregate[x]
            else:
                sums_persistence[self.user_index[x]] += counts[x]
                avg_persistence[self.user_index[x]] += aggregate[x]
        for x in avg_persistence:
            avg_persistence[x] = round(math.log(avg_persistence[x] + 1, log_base), 2)
        return [sums_persistence, avg_persistence]

    @staticmethod
    def __total_random(n):
        """
        List of random colors

        :param n: total number of colors to return
        :type n: int
        :return: returns a random list of tuples containing RGB color schemes
        :rtype: list (list of tuples)
        """
        colors = []
        for x in range(0, n):
            colors.append([random.randrange(0, 255), random.randrange(0, 255), random.randrange(0, 255)])
        return [(i[0], i[1], i[2]) for i in colors]

    def html_print(self):
        """
        Lazy function for displaying in HTML the state of code after last update()

        :return: html code
        :rtype: str
        """
        results = self.calculate_ownership()
        # Creating styles for visual representation in HTML
        spaced_colors = self.__total_random(len(set(self.user_index.values())))
        html = """<html><head><style>
        [tooltip]:before {
        /* needed - do not touch */
        content: attr(tooltip);
        position: absolute;
        opacity: 0;
    
        /* customizable */
        transition: all 0.15s ease;
        padding: 10px;
        color: #333;
        border-radius: 10px;
        box-shadow: 2px 2px 1px silver;    
        }

        [tooltip]:hover:before {
        /* needed - do not touch */
        opacity: 1;
    
        /* customizable */
        background: yellow;
        margin-top: -50px;
        margin-left: 20px;    
        }

        [tooltip]:not([tooltip-persistent]):before {
        pointer-events: none;
        }
        """
        i = 0  # auxiliary variable
        hashed_codes = dict()
        names_div = "<table>"
        names_div += "<tr><td>Names</td><td>Characters Survived</td><td>Persistence</td></tr>"
        for x in sorted(set(self.user_index.values())):
            # first letter added to comply with CSS naming
            hashed_codes[x] = "a%s" % (hashlib.md5(x.decode("utf-8").encode("utf-8")).hexdigest())
            html += ".%s{background-color:rgb%s}" % (hashed_codes[x], str(spaced_colors[i]))
            names_div += "<tr><td><span  class = '%s'>%s</span></td><td>%s</td><td>%s</td></tr>" % \
                         (hashed_codes[x], x.decode("utf-8"), str(results[0].get(x, 0)), str(results[1].get(x, 0)))
            i += 1
        names_div += "</table>"
        html += "</style></head><body><div style='float:left'>"
        i = 0
        for x in self.code:
            if self.code_text[i] == "\n":
                html += "<br />"
            else:
                html += "<span tooltip='%s' class = '%s'>%s</span>" % \
                        (self.user_index[x].decode("utf-8"), hashed_codes[self.user_index[x]], self.code_text[i])
            i += 1
        html += "</div><div style='float:right'>"
        html += names_div
        html += "</div></body></html>"
        return html


if __name__ == "__main__":
    # Elementary test example cases

    rev1 = """void BanManager::save()
    {
        JMutexAutoLock lock(m_mutex);
        dstream<<"BanManager: saving to "<<m_banfilepath<<std::endl;
        std::ofstream os(m_banfilepath.c_str(), std::ios::binary);
        
        if(os.good() == false)
        {
            dstream<<"BanManager: failed loading from "<<m_banfilepath<<std::endl;
            throw SerializationError("BanManager::load(): Couldn't open file");
        }
    
        for(std::set<std::string>::iterator
                i = m_ips.begin();
                i != m_ips.end(); i++)
        {
            if(*i == "")
                continue;
            os<<*i<<"\n";
        }
        m_modified = false;
    }"""

    rev2 = """void BanManager::save()
    {
        JMutexAutoLock lock();
        infostream<<"BanManager: saving to "<<m_banfilepath<<std::endl;
        std::ofstream os(m_banfilepath.c_str(), std::ios::binary);
        
        if(os.good() == false)
        {
            infostream<<"BanManager: failed saving to "<<m_banfilepath<<std::endl;
            throw SerializationError("BanManager::load(): Couldn't open file");
        }
    
        for(std::map<std::string, std::string>::iterator
                i = m_ips.begin();
                i != m_ips.end(); i++)
        {
            os<<i->first<<"|"<<i->second<<"\n";
        }
        m_modified = false;
    }"""

    rev3 = """void BanManager::save()
    {
        JMutexAutoLock lock(m_mutex);
        infostream<<"BanManager: saving to "<<m_banfilepath<<std::endl;
        std::ostringstream ss(std::ios_base::binary);
        
        for(std::map<std::string, std::string>::iterator
                i = m_ips.begin();
                i != m_ips.end(); i++)
        {
            ss << i->first << "|" << i->second << "\n";
        }
    
        if(!fs::safeWriteToFile(m_banfilepath, ss.str())) {
            infostream<<"BanManager: failed saving to "<<m_banfilepath<<std::endl;
            throw SerializationError("BanManager::load(): Couldn't write file");
        }
    
        m_modified = false;
    }"""

    file1 = GitPersistence(rev1, "user1".encode("utf-8"))
    file1.update(rev2, "user2".encode("utf-8"))
    file1.update(rev3, "user3".encode("utf-8"))
    with open("diff.html", "w") as text_file:
        text_file.write(file1.html_print())
    print(file1.calculate_ownership())
