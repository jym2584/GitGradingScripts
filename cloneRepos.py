import yaml
import subprocess
from threading import Thread
import requests
from git import Repo,GitCommandError
import datetime
import shutil
import csv
import re
import os
import time
import repo_utils
import pprint
pp = pprint.PrettyPrinter(indent=4)

"""
This script contains logic for cloning git repositories

TODO: 
- Store stdout/clone logs onto the assignment folder
- Grade classwork activities more easily
    - This just would be in the form of supplying a yaml file with a list of files (or probably paths?) to look at, and searches the contents of the file (if there is even a file)
- Make the roster path optional. If the roster path is left out blank, then it should just clone every git repository in the organization
- Re-structure code into separate classes/files 


"""
CONFIG_PATH = "config/config.yml"
CONFIG = dict()
SUBMISSIONS = dict() # information about student submissions. mapping of the student's git identifier to their number of commits and the commit hash
ORGANIZATION = None # selected organization from user input
CLONE_PATH = None # clone_output_path/<organization_name>/
STUDENTS = dict() # mapping of identifier to student name
STUDENTS_NO_SUBMISSIONS = dict()
STUDENTS_NOT_CLONED = dict()
LIGHT_GREEN = '\033[1;32m' # Ansi code for light_green
LIGHT_YELLOW = '\033[1;33m' # Ansi code for light_yellow
LIGHT_RED = '\033[1;31m' # Ansi code for light_red
WHITE = '\033[0m' # Ansi code for white to reset back to normal text
# Enable color in cmd
if os.name == 'nt':
    os.system('color')

class RepoThread(Thread):
    """A thread that handles the pulling of student github repositories 
    """
    global SUBMISSIONS
    
    def __init__(self, identifier, student_name, assignment_name, timestamp_pulled):
        super().__init__()
        self.__git_identifier = identifier
        self.__student_name = student_name 
        self.__assignment_name = assignment_name
        self.__clone_url = f"https://{CONFIG['github_classic_token']}@github.com/{ORGANIZATION['identifier']}/{self.__assignment_name}-{self.__git_identifier}.git"
        self.__timestamp_pulled = timestamp_pulled
        self.__clone_path = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/{self.__assignment_name}-{self.__student_name}"
        self.__repo = None
        self.__submission_info = None
    
    def run(self):
        # clone the repository
        try: self.clone_repository()
        except GitCommandError as gce:
            self.print_clone_error(gce)
            global STUDENTS_NOT_CLONED
            STUDENTS_NOT_CLONED[self.__git_identifier] = {'student_name': self.__student_name, 'clone_url': self.__clone_url}
            return
        
        if self.__submission_info:
            # checks if there are new commits
            if not self.__submission_info.is_submitted(SUBMISSIONS):
                print(f"{LIGHT_YELLOW}Cloned (WITH WARNINGS) {self.__student_name} ({self.__git_identifier}) because there is no submission at the time of pull.{WHITE}")
                # get before and after pull commits
                print(f"\tCurrent commit: {self.__submission_info.get_commit_hash_stored(SUBMISSIONS)} ({self.__submission_info.get_commit_length_stored(SUBMISSIONS)} total commits)")
                try:
                    print(f"\tLatest commit:")
                    print(f"\t\tHash: {self.__submission_info.get_commit_hash_latest()} ({self.__submission_info.get_commit_length_latest()} total commits)")
                    print(f"\t\tAuthor:  {self.__submission_info.get_commit_latest().author}")
                    print(f"\t\tMessage: {self.__submission_info.get_commit_latest().message.strip()}")
                except: pass
                print(f"\tClone URL: {self.__clone_url}")
                global STUDENTS_NO_SUBMISSIONS
                STUDENTS_NO_SUBMISSIONS[self.__git_identifier] = {'student_name': self.__student_name, 'clone_url': self.__clone_url}
                #self.delete_repository_soft()
                return
            
            self.__submission_info.update_submission_info(SUBMISSIONS)
            
        print(f"{LIGHT_GREEN}Cloned {self.__student_name} ({self.__git_identifier}){WHITE}")
    
    def clone_repository(self):
        """Clones a repository
        
        TODO: Try cloning through subprocess if getting the below warning
        error: invalid path 'src/main/java/unit01/scavenger_hunt/CA ALTERNATIVE?.png'
        fatal: unable to checkout working tree
        warning: Clone succeeded, but checkout failed.
        You can inspect what was checked out with 'git status'
        and retry with 'git restore --source=HEAD :/'
        """
        self.__repo = Repo.clone_from(self.__clone_url, self.__clone_path)
        if CONFIG['log_submissions']:
            self.__submission_info = repo_utils.Submission(self.__git_identifier, ORGANIZATION['name'], self.__assignment_name, SUBMISSIONS, self.__repo)
          
    # TODO: Need to resolve PermissionErrors with a process using the git repo (and errors related to moving the .git folder as well)
    # def delete_repository_soft(self):
    #     """Soft deletes the git repository by renaming it into a no submission list
    #     """
    #     self.__repo = None
    #     source = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/{self.__assignment_name}-{self.__student_name}"
    #     dest = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/1. NO SUBMISSIONS/{self.__assignment_name}-{self.__student_name}"
    #     time.sleep(2)
    #     shutil.move(source, dest)
    
    def print_clone_error(self, git_exception: GitCommandError):
        stderr_dict = parse_git_exception(git_exception)
        stderr_message = "there is an error while cloning the repository."
        detailed = True
        if 'err_remote' in stderr_dict and "Repository not found." in stderr_dict['err_remote']:
                stderr_message = "the repository doesn't exist."
                detailed = False
        if 'err_warning' in stderr_dict and "Clone succeeded, but checkout failed." in stderr_dict['err_warning']: # TODO: force clone the repository (using subprocess?)
            stderr_message = "there is something wrong with the contents of the repository (clone this repository manually)."
        print(f"{LIGHT_RED}Skipping {self.__student_name} ({self.__git_identifier}) because {stderr_message}{WHITE}")
        if detailed: print(stderr_dict['stderr'])
            

def parse_git_exception(git_exception: GitCommandError):
    """Retrieves stderr messages from a git exception

    Args:
        stderr (_type_): _description_

    Returns:
        _type_: _description_
    """
    stderr = git_exception.stderr
    stderr_dict = {'stderr': stderr}
    
    # initialize the types of errors that are thrown by git
    error = re.compile(r'error: (.+)')
    error_match = error.search(stderr)
    if error_match: stderr_dict['err_error'] = error_match.group(1)
    
    remote = re.compile(r'remote: (.+)')
    remote_match = remote.search(stderr)
    if remote_match: stderr_dict['err_remote'] = remote_match.group(1)
    
    fatal = re.compile(r'fatal: (.+)')
    fatal_match = fatal.search(stderr)
    if fatal_match: stderr_dict['err_fatal'] = fatal_match.group(1)

    warning = re.compile(r'warning: (.+)')
    warning_match = warning.search(stderr)
    if warning_match: stderr_dict['err_warning'] = warning_match.group(1)
    
    return stderr_dict
          
def import_config():
    """Imports configuration settings from the CONFIG_PATH yaml file

    Returns:
        dict: Parsed config file to use in the script
    """
    config = dict()
    with open(CONFIG_PATH, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    if not config['organizations']: raise RuntimeError(f"You must add at least one organization to the configuration file.\nEdit the configuration file on {CONFIG_PATH}")
    if not config['clone_output_path'] or not config['github_classic_token']: raise RuntimeError(f"You must fill out the REQUIRED variables on the config file to run the script.\nEdit the config file on {CONFIG_PATH}")
    return config

def import_roster():
    """Imports the student roster from the selected organization (user input)

    Returns:
        _type_: _description_
    """
    students = dict()
    warnings = False
    with open(ORGANIZATION['roster_path'], 'r') as file:
        reader = csv.reader(file)
        next(reader)
        line_num = 1
        for record in reader:
            line_num+=1
            student_name = re.sub(r'[. ]', '', re.sub(r'(, )|(,)', '-', record[0]).split(' ')[0])
            github_identifier = record[1]
            if not student_name: student_name = None
            if github_identifier: 
                students[github_identifier] = student_name # github_username, identifier
            else:
                print(f"{LIGHT_RED} (!) Ignoring record (line {line_num}) from the student roster since it does not contain a git identifier.{WHITE}\n\t{record}")
                warnings = True
    if warnings: print(f"\nCheck your classroom roster csv file from `{ORGANIZATION['roster_path']}`\n")
    return students



def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def is_token_valid(token):
    """Checks if the provided GitHub token is valid

    Args:
        token (str): the github token
    """
    request = requests.get("https://api.github.com/user", headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    return request.ok
    
    
def main():
    global CONFIG
    global ORGANIZATION
    global CLONE_PATH
    global STUDENTS
    clear_terminal()
    print(f"Importing config from {CONFIG_PATH}...\n")
    CONFIG = import_config()
    
    # check if the token is valid
    token_valid = is_token_valid(CONFIG['github_classic_token'])
    if not token_valid:
        print(f"{LIGHT_RED}(!) Your GitHub access token is invalid.{WHITE}")
        print("Ensure that the token has 1) not expired and/or 2) your token has been granted sufficient permissions to read and clone git repositories.")
        return
    
    confirm_organization = False
    assignment_name = None
    
    # pull assignments from organization and student rosters (user inputs)
    while not confirm_organization:
        # prompt for organization
        if len(CONFIG['organizations']) == 1: ORGANIZATION = CONFIG['organizations'][0]
        # multiple organizations
        elif len(CONFIG['organizations']) > 1:
            orgs = CONFIG['organizations']
            while True:
                org_input = None
                print("Organizations:")
                for i in range(0, len(CONFIG['organizations'])): print(f"\t{i + 1}. {orgs[i]['name']} ({orgs[i]['identifier']})")
                
                
                try: org_input = int(input("Select an organization (num input): ")) 
                except: pass
                try:
                    if org_input <= 0:raise ValueError("No inputs less than or equal to 0")
                    ORGANIZATION = CONFIG['organizations'][org_input - 1]
                    break
                except: 
                    clear_terminal()
                    print("Invalid organization number.") 
        
        # get clone path from selected organization
        CLONE_PATH = f"{CONFIG['clone_output_path']}/{ORGANIZATION['name']}"
        # pull student rosters from organization
        print(f"\nPulling student rosters from `{ORGANIZATION['name']} ({ORGANIZATION['identifier']})`...")
        STUDENTS = import_roster()
        
        # prompt for assignment name
        assignment_name = None
        while not assignment_name: 
            assignment_name = input(f"Assignment Name (or enter to re-select organization): ").replace(" ", "-")
            if assignment_name: 
                confirm_organization = True # end initial loop chain
            else:
                clear_terminal()
                break
    
    timestamp_pulled = datetime.datetime.strftime(datetime.datetime.now(), '%m-%d-%Y-%H-%M-%S') # github classroom styled format
    
    # initialize submission logs
    if CONFIG['log_submissions']:
        global SUBMISSIONS
        SUBMISSIONS = repo_utils.import_submissions(ORGANIZATION['name'], ORGANIZATION['identifier'], timestamp_pulled, assignment_name)
        
    # pull repos
    threads = []
    for identifier, student_name in STUDENTS.items():
        thread = RepoThread(identifier, student_name, assignment_name, timestamp_pulled)
        threads.append(thread)

    print()
    clone_message = f"Cloning to: `{CLONE_PATH}/{assignment_name}-{timestamp_pulled}/`..."
    print("-" * len(clone_message))
    print(clone_message)
    print(f"Timestamp pulled: {timestamp_pulled}")
    print("-" * len(clone_message))
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    
    # Statistics
    print ("-" * 11)
    print("STATISTICS: ")
    print ("-" * 11)
    # cloned
    print(f"{LIGHT_GREEN}Successfully cloned {len(STUDENTS) - len(STUDENTS_NOT_CLONED)}/{len(threads)} repositories...{WHITE}")
    # not cloned
    if STUDENTS_NOT_CLONED:
        print(f"...{LIGHT_RED}`{len(STUDENTS_NOT_CLONED)}` of which were not cloned (double check this!):{WHITE}")
        for identifier, info in STUDENTS_NOT_CLONED.items():
            print(f"\t{info['student_name']} ({identifier})")
            print(f"\t\tClone URL: {info['clone_url']}")
    print()
    # no submissions
    if STUDENTS_NO_SUBMISSIONS:
        print(f"{LIGHT_YELLOW}`{len(STUDENTS_NO_SUBMISSIONS)}` of which did not have an active submission since time of pull ({timestamp_pulled}):{WHITE}")
        for identifier, info in STUDENTS_NO_SUBMISSIONS.items():
            print(f"\t{info['student_name']} ({identifier})")
            #print(f"\t\tClone URL: {info['clone_url']}")
        print()
    
    # log submissions
    if CONFIG['log_submissions']:
        repo_utils.save_submissions(SUBMISSIONS)
        print(f"Uploaded submission logs to {repo_utils.SUBMISSION_LOGS}.")

if __name__ == "__main__":
    main()