from git import Repo
import yaml
from threading_utils import synchronized
from dateutil.relativedelta import relativedelta
from datetime import datetime
import os
import platform
import pprint
import shutil
import subprocess
pp = pprint.PrettyPrinter(indent=4)

SUBMISSION_LOGS = "config/submissions.yml" # logs submissions since last pull
BAD_AUTHORS = {"github-classroom[bot]"} 
BAD_COMMIT_MESSAGES = {"Add files via upload"} # commit messages that might indicate that they're using AI code in some way

class Submission:
    def __init__(self, identifier:str, organization_name: str, assignment_name: str, submissions_dict: dict, repo:Repo):
        """Statistics about a student's submission

        Args:
            identifier (str): git identifier
            organization_name (str): organization name of the submission
            assignment_name (str): assignment name of the submission
            timestamp_pulled (str): timestamp when the submission was pulled
            submissions_dict (dict): Submissions dictionary
            repo (Repo): git repository associated with the submission
        """
        self.__git_identifier = identifier
        self.__organization_name = organization_name
        self.__assignment_name = assignment_name
        self.__repo = repo
        self.__commits = list(self.__repo.iter_commits())
        
        # Add the student to the submissions dictionary if their repository is being pulled for the first time
        if self.__git_identifier not in submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions']:
            submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions'][self.__git_identifier] = {'num_commits': 0, 'commit_hash': None}

    @synchronized
    def update_submission_info(self, submissions_dict: dict):
        """ Updates the submission information to a submission dictionary
        
        Args:
            submissions_dict (dict): Submissions dictionary
        """  
        submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions'][self.__git_identifier]['num_commits'] = self.get_commit_length_latest()
        submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions'][self.__git_identifier]['commit_hash'] = self.get_commit_hash_latest()

    def get_commits(self):
        return self.__commits
    
    def get_commit_latest(self):
        return self.__commits[0]
    
    def get_commit_hash_latest(self):
        return self.__commits[0].hexsha
    
    def get_commit_hash_stored(self, submissions_dict:dict) -> str:
        """Gets the commit hash stored in the submissions dictionary

        Args:
            submissions_dict (dict): Submissions dictionary

        Returns:
            str: Commit hash
        """
        return submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions'][self.__git_identifier]['commit_hash']

    def get_commit_length_latest(self) -> int:
        return len(self.__commits)
    
    def get_commit_length_stored(self, submissions_dict:dict) -> int:
        """Gets the number of commits that is stored in the submissions dictionary

        Args:
            submissions_dict (dict): Submissions Dictionary

        Returns:
            int: number of commits stored for the user
        """
        return submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]['submissions'][self.__git_identifier]['num_commits']
    
    def is_submitted(self, submissions_dict:dict) -> bool:
        """Checks if there is a submission

        Returns:
            bool: Whether or not a submission is considered "submitted"
        """
        if self.get_commit_length_latest() == 0 or str(self.__commits[0].author) in BAD_AUTHORS:
            return False
        # checks if there are new commits from the last pull
        if self.get_commit_hash_stored(submissions_dict) == self.get_commit_hash_latest():
            return False
        return True 
    

def import_submissions(organization_name, organization_identifier, timestamp_pulled, assignment_name) -> dict:
    """Imports submissions from a yaml file

    Args:
        organization_name (str): Organization Name (full)
        organization_identifier (str): Organization identifier
        timestamp_pulled (str): timestamp that the submission is pulled at 
        assignment_name (str): Name of the assignment

    Returns:
        dict: Submissions dictionary
    """
    config = dict()
    with open(SUBMISSION_LOGS, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        
        if config['organizations'] is None:
            config['organizations'] = dict()
        
        if organization_name not in config['organizations']:
            config['organizations'][organization_name] = {
                'identifier': organization_identifier, 
                'submission_history': dict()
            }
        
        # add new assignment
        if assignment_name not in config['organizations'][organization_name]['submission_history']:
            config['organizations'][organization_name]['submission_history'].update({
                assignment_name: {
                    'last_pulled': None,
                    'submissions': dict()
                } 
            })
            
        config['organizations'][organization_name]['submission_history'][assignment_name]['last_pulled'] = timestamp_pulled

    return config 

def save_submissions(submissions_dict: dict):
    """Saves the modified submissions dictionary

    Args:
        submissions_dict (dict): Submissions dictionary
    """
    with open(SUBMISSION_LOGS, 'w') as file:
        yaml.dump(submissions_dict, file)


def parse_duration_string(delta_string:str):
    """Parses the duration string to a format that is datetime compatible

    Args:
        delta_string (str): Time in string
            d - day
            h - hour
                    
            i.e. 
            - 90d = 90 days
            - 12h = 12 hours
            - 90d12h = 90 days and 12 hours
        

    Returns:
        relativedelta: time interval that is datetime compatible (i.e. 90days 12hours)
    """
    duration = relativedelta()
    
    current_value = '' # parsing integer values
    for char in delta_string:
        if char.isdigit(): current_value += char
        else:
            unit = char.lower()
            if current_value:
                value = int(current_value)
                if unit == 'd': # day
                    duration = duration + relativedelta(days=value)
                elif unit == 'h': # hour
                    duration = duration + relativedelta(hours=value)
                elif unit == 'm': # minute
                    duration = duration + relativedelta(minutes=value)
                # elif unit == 's': # seconds
                #     duration = duration + relativedelta(seconds=value)
                current_value = ''
    return duration

def get_file_creation_time(file_path):
    if platform.system() == 'Windows': creation_time = os.path.getctime(file_path)
    else:
        # Use stat to get the creation time on linux systems
        stat_info = os.stat(file_path)
        try: creation_time = stat_info.st_birthtime
        except AttributeError: creation_time = stat_info.st_mtime # use st_mtime as a fallback

    return datetime.fromtimestamp(creation_time)

def prune_local_repos(clone_output_path:str, delta_string:str, prompt_removal:bool):
    """Removes local repositories that are cloned by the script

    Args:
        clone_output_path (str): Output path to search and delete files
        remove_before_timestamp (datetime): Remove folders older than this timestamp
        prompt_removal (bool): Determines whether a prompt is required to remove files from the local system
    """
    
    dirs_to_remove = dict()
    searched_paths = set()
    
    timestamp_now = datetime.now()
    remove_before_timestamp = timestamp_now - parse_duration_string(delta_string)
    # grab files that are older than the timestamp
    for dir_parent in os.listdir(clone_output_path):
        directory_path = f"{clone_output_path}/{dir_parent}/"
        for directory_name in os.listdir(directory_path):
            full_path = f"{directory_path}{directory_name}/"
            path_timestamp = get_file_creation_time(full_path)
            
            if remove_before_timestamp > path_timestamp: # remove everything before path_timestamp 
                dirs_to_remove[directory_name] = {'created_timestamp': path_timestamp, 'full_path': full_path}
                searched_paths.add(directory_path)
    
    if len(dirs_to_remove) == 0:
        return
    
    print("--------------------DIRECTORIES TO DELETE----------------------")
    print("Searched paths:")
    for path in searched_paths: print(f"- {path}")
    print()
    print(f"Current timestamp         :  {timestamp_now}")
    print(f"Deleting files older than :  {remove_before_timestamp}")
    print(f"Difference                :  {delta_string}")
    print("---------------------------------------------------------------")
    for dir in dirs_to_remove:
        print(f"- {dir} (created: {dirs_to_remove[dir]['created_timestamp']})")
    print()
    if prompt_removal:
        prompt = input("Do you want to delete these files? (`yes` for yes; any other input for no): ")
        if not prompt:
            print("Not deleting the above files.")
            return
    
    print("---------------------DELETING DIRECTORIES----------------------")
    for dir in dirs_to_remove:
        path = dirs_to_remove[dir]['full_path']
        try: 
            shutil.rmtree(path)
        except Exception as e: 
            print(f"(!) Cannot delete {path}\n{e}\n")
            
    print("Done!")


def prune_old_submissions_logs(delta_string:str):
    pass
    


if __name__ == "__main__":
    pass

    prune_local_repos("E:/GitHub/GithubClassroomScripts/assignments", "0m", True)
        
# organization_name = "My Test Org"
# assignment_name = "Test-assignment"

# config = import_submissions(organization_name, "test-org", '2024-01-23 22:33:44', assignment_name)
# pp.pprint(config)
# repo = Repo("E:/GitHub/GithubClassroomScripts/assignments/Patric (22355)/unit01-01-21-2024-21-01-45/unit01-12-Agwai-CJ")
# submission = Submission("Agwai-CJ", organization_name, assignment_name, config, repo)

# submission.update_submission_info(config, submission.get_commit_length_latest(), submission.get_commit_hash_latest())
# pp.pprint(config)
# save_submissions(config)