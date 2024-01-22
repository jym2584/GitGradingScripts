import yaml
import subprocess
from threading import Thread
import requests
from git import Repo
import datetime
import shutil
import csv
import re
import os
import time

CONFIG_PATH = "config/config.yml"
CONFIG = {}
ORGANIZATION = None # selected organization from user input
CLONE_PATH = None # clone_output_path/<organization_name>/
STUDENTS = dict() # mapping of identifier to student name
STUDENTS_NO_SUBMISSIONS = dict()
STUDENTS_NOT_CLONED = dict()
LIGHT_GREEN = '\033[1;32m' # Ansi code for light_green
LIGHT_RED = '\033[1;31m' # Ansi code for light_red
WHITE = '\033[0m' # Ansi code for white to reset back to normal text
# Enable color in cmd
if os.name == 'nt':
    os.system('color')

class RepoThread(Thread):
    """A thread that handles the pulling of student github repositories 
    """
    
    def __init__(self, identifier, student_name, assignment_name, timestamp_pulled):
        super().__init__()
        self.__git_identifier = identifier
        self.__student_name = student_name 
        self.__assignment_name = assignment_name
        self.__clone_url = f"https://github.com/{ORGANIZATION['identifier']}/{self.__assignment_name}-{self.__git_identifier}.git"
        self.__timestamp_pulled = timestamp_pulled
        self.__clone_path = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/{self.__assignment_name}-{self.__student_name}"
        self.__repo = None
        self.__commits = None
    
    def run(self):
        # clone the repository
        try: self.clone_repository()
        except Exception as e:
            print(f"{LIGHT_RED}Skipping {self.__student_name} ({self.__git_identifier}) because the repository does not exist.{WHITE}")
            print(e)
            global STUDENTS_NOT_CLONED
            STUDENTS_NOT_CLONED[self.__git_identifier] = {'student_name': self.__student_name, 'clone_url': self.__clone_url}
            return
        
        # checks if there are new commits
        if not self.submitted():
            print(f"{LIGHT_RED}Cloned (WITH WARNINGS) {self.__student_name} ({self.__git_identifier}) because there is no submission at the time of pull.{WHITE}")
            # get before and after pull commits
            current_commits = 0
            try: current_commits = len(self.__commits)
            except: pass
            print(f"\tNum commits since last pulled: <before> --> {current_commits}") # TODO
            try:
                print("\tLatest commit:")
                print(f"\t\tAuthor:  {self.__commits[0].author}")
                print(f"\t\tMessage: {self.__commits[0].message}")
            except:
                pass
            print(f"\tClone URL: {self.__clone_url}")
            global STUDENTS_NO_SUBMISSIONS
            STUDENTS_NO_SUBMISSIONS[self.__git_identifier] = {'student_name': self.__student_name, 'clone_url': self.__clone_url}
            #self.delete_repository_soft()
            return
    
        print(f"{LIGHT_GREEN}Cloned {self.__student_name} ({self.__git_identifier}){WHITE}")
    
    def clone_repository(self):
        self.__repo = Repo.clone_from(self.__clone_url, self.__clone_path)
        self.__commits = list(self.__repo.iter_commits())
        
    def get_commits(self):
        return self.__commits

    def submitted(self):
        # checks if there is no submission
        if len(self.__commits) == 0 or str(self.__commits[0].author) == "github-classroom[bot]":
            return False
        # checks if there are new commits from the last pull
        return True
   
    # TODO: Need to resolve PermissionErrors with a process using the git repo (and errors related to moving the .git folder as well)
    # def delete_repository_soft(self):
    #     """Soft deletes the git repository by renaming it into a no submission list
    #     """
    #     self.__repo = None
    #     source = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/{self.__assignment_name}-{self.__student_name}"
    #     dest = f"{CLONE_PATH}/{self.__assignment_name}-{self.__timestamp_pulled}/1. NO SUBMISSIONS/{self.__assignment_name}-{self.__student_name}"
    #     time.sleep(2)
    #     shutil.move(source, dest)
                
def import_config():
    """Imports configuration settings from the CONFIG_PATH yaml file

    Returns:
        dict: Parsed config file to use in the script
    """
    config = dict()
    with open(CONFIG_PATH, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    if len(config['organizations']) == 0 or not config['github_classic_token'] or not config['clone_output_path']: raise RuntimeError("You must fill out the entire configuration file to run the script.\nEdit the configuration file on {CONFIG_PATH}")
    return {'github_classic_token': config['github_classic_token'], 'clone_output_path': config['clone_output_path'], 'organizations': config['organizations']}

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
    
def main():
    global CONFIG
    global ORGANIZATION
    global CLONE_PATH
    global STUDENTS
    clear_terminal()
    print(f"Importing config from {CONFIG_PATH}...\n")
    CONFIG = import_config()
    
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
    
    # pull repos
    threads = []
    timestamp_pulled = datetime.datetime.strftime(datetime.datetime.now(), '%m-%d-%Y-%H-%M-%S') # github classroom styled format
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
    print(f"{LIGHT_GREEN}Successfully cloned {len(STUDENTS) - len(STUDENTS_NOT_CLONED)}/{len(threads)} repositories.\n{WHITE}")
    # not cloned    
    print(f"{LIGHT_RED}`{len(STUDENTS_NOT_CLONED)}` repositories were not cloned (double check this!):{WHITE}")
    for identifier, info in STUDENTS_NOT_CLONED.items():
        print(f"\t{info['student_name']} ({identifier})")
        print(f"\t\tClone URL: {info['clone_url']}")
    print()
    # no submissions
    print(f"{LIGHT_RED}`{len(STUDENTS_NO_SUBMISSIONS)}` of which did not have an active submission since time of pull ({timestamp_pulled}):{WHITE}")
    for identifier, info in STUDENTS_NO_SUBMISSIONS.items():
        print(f"\t{info['student_name']} ({identifier})")
        print(f"\t\tClone URL: {info['clone_url']}")
    print()
    #print("Uploaded submission logs to config/submissions.yml.")

if __name__ == "__main__":
    main()