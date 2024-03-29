# Grading Scripts for Github Classroom
This repository contains grading scripts to assist in grading assignments managed by GitHub Classroom. 

Currently, the clone repository script (`cloneRepos.py`) pulls student repositories from a CSV file containing the student roster (pulled from GitHub classroom) and handles non-submissions.

The format is (same as the github classroom roster CSV file):
| identifier   | github_username |
|--------------|------------------|
| Last, First  | git_username     |
| LastFirst    | git_username2    |


Additionally, the script assumes that you're already authenticated within the correct GitHub account to run the script and access the organizations of interest.

Theoretically, this can also work for group assignments. It would be ideal to create a separate CSV file/organization record, adhering to the format below (same as github classroom):

| identifier | github_username |
|------------|------------------|
| Group 1    | group_1_repo     |
| Group 2    | group_2_repo     |

## Instructions:
- Clone or download the github repository.
- Fill out the configuration file located at `config/config.yml`
    > - **github_classic_token**: This is used for authenticating into github repositories using an access token. A later compatibility will be implemented for running this script on other git hosting services (github, gitlab, bitbucket)
    > - **clone_output_path** : Full directory path (ideal) of where you want to download github repositories to (i.e. "E:/GitHub/assignments-2235/")
    > - **organizations**: Key value pair mapping of the organization's:
    >   - **name**: This can be anything you want. It's just an easier way to identify a class/split if they are in the same organization 
    >   - **identifier**: GitHub Organization identifier
    >   - **roster_path**: full directory path of the classroom roster (from github classroom)
    >
    > You can also add multiple organizations for these following example use cases if you:
    > - Manage multiple classrooms from different organizations
    > - Manage multiple classrooms from the same organization
    > - Want to split the classroom roster from an organization
- Install the required python dependencies using `pip install -r requirements.txt`
- Run the python script using `py cloneRepos.py` or the batch script.

## Future
- Use tokens to pull git repositories if pulling from different git hosting services
- Integrate the MOSS script (and possibly [JPlag](https://github.com/jplag/JPlag)) to detect possible plagarism/duplicate code in student submissions
- Done! ~~Store the commit count for each student to determine if a student repo has been updated since the time of pull (easier for grading)~~
- Possible GUI interface?
- Pull git repositories from a certain date/time. If you're planning to roll back student repositories to a certain date/time, you just have to be aware that commit times can be changed. There's no workaround other than just pulling the repositories at the time of pull or instilling a bit of trust to the students.
