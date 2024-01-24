from git import Repo
import yaml
from threading_utils import synchronized
import pprint
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
        if self.__git_identifier not in submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name]:
            submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name][self.__git_identifier] = {'num_commits': 0, 'commit_hash': None}

    @synchronized
    def update_submission_info(self, submissions_dict: dict):
        """ Updates the submission information to a submission dictionary
        
        Args:
            submissions_dict (dict): Submissions dictionary
        """  
        submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name][self.__git_identifier]['num_commits'] = self.get_commit_length_latest()
        submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name][self.__git_identifier]['commit_hash'] = self.get_commit_hash_latest()

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
        return submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name][self.__git_identifier]['commit_hash']

    def get_commit_length_latest(self) -> int:
        return len(self.__commits)
    
    def get_commit_length_stored(self, submissions_dict:dict) -> int:
        """Gets the number of commits that is stored in the submissions dictionary

        Args:
            submissions_dict (dict): Submissions Dictionary

        Returns:
            int: number of commits stored for the user
        """
        return submissions_dict['organizations'][self.__organization_name]['submission_history'][self.__assignment_name][self.__git_identifier]['num_commits']
    
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
            config['organizations'][organization_name] = {'identifier': organization_identifier, 'last_pulled': None,'submission_history': dict()}
        config['organizations'][organization_name]['last_pulled'] = timestamp_pulled
        if assignment_name not in config['organizations'][organization_name]['submission_history']:
            config['organizations'][organization_name]['submission_history'] = {assignment_name: dict()}
        
    return config 

def save_submissions(submissions_dict: dict):
    """Saves the modified submissions dictionary

    Args:
        submissions_dict (dict): Submissions dictionary
    """
    with open(SUBMISSION_LOGS, 'w') as file:
        yaml.dump(submissions_dict, file)

# organization_name = "My Test Org"
# assignment_name = "Test-assignment"

# config = import_submissions(organization_name, "test-org", '2024-01-23 22:33:44', assignment_name)
# pp.pprint(config)
# repo = Repo("E:/GitHub/GithubClassroomScripts/assignments/Patric (22355)/unit01-01-21-2024-21-01-45/unit01-12-Agwai-CJ")
# submission = Submission("Agwai-CJ", organization_name, assignment_name, config, repo)

# submission.update_submission_info(config, submission.get_commit_length_latest(), submission.get_commit_hash_latest())
# pp.pprint(config)
# save_submissions(config)