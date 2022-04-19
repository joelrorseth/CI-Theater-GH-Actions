# CI Theater in GitHub Actions

**Abstract:**
Having been adopted as a standard development practice in many open-source software
projects, continuous integration (CI) provides many benefits when its practices
are employed effectively. However, these well-established benefits are easily
negated when the principles of CI are not adhered to. In this study,
we empirically analyze the prevalence of this neglect, dubbed
*Continuous Integration Theater*, across open-source GitHub software projects
that employ the GitHub Actions CI tool. Specifically, we analyze 1,156 projects to
quantify four CI theater anti-patterns, namely infrequent commits to mainline, poor
test coverage, lengthy broken build periods, and lengthy builds. We determine that
commits are infrequent in 78.03% of studied projects, and that the average test
coverage is only 68.37%. However, the duration of builds and broken build periods
are not typically excessive, nor are they particularly common. Our analyses do
reveal significant disparity between projects of different programming languages,
with respect to different CI theater anti-patterns and project sizes.

## Installation
First, install the required dependencies into a virtual environment. Note that
these steps have only been tested with Python 3.8.10.
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To run the experiments, you will need a snapshot of GHTorrent. Use the following command
to download the snapshot from the paper, dated March 6 2021. Note that the full
uncompressed folder will take around 539GB of space.

```
wget -bqc ghtorrent-downloads.ewi.tudelft.nl/mysql/mysql-2021-03-06.tar.gz
```

Unzip the file, and make note of the full path to the newly created `github-2021-03-06`
folder for the next step.


## Running the Experiment

The entire experiment can be executed via `main.py`, however a few environment variables
must be set beforehand. You will need a GitHub personal access token to allow the
program to query the GitHub API. You will also need the full path to the GHTorrent
snapshot, as mentioned previously. Here is a convenient script to set all variables
and run `main.py` (name it something like `run-main.sh`):

```
api_username="my_github_username" \
api_password="my_github_token_here" \
github_base_url="https://api.github.com" \
coveralls_base_url="https://coveralls.io" \
ghtorrent_path="/my_path_here/github-2021-03-06/" \
python -u main.py
```

The experiment operates in 3 sequential phases. First, the projects from the GHTorrent
dataset are filtered, using various criteria and some additional data retrieved from the
Github API. The second phase augments the selected projects with additional data, namely
the workflow files and run history. Note that a few additional filter operations are
applied during this phase. The final phase analyzes the curated data, printing various
statistics and rendering various charts to the `results` directory. Several other
config variables are hardcoded in `config.py`, if you wish to change certain experiment
parameters

## API Limits

GitHub has an API limit of 5000 calls per hour for registered users, which is why
the personal access token is required for our experiment. Due to the number of projects
in various stages of our filtering process, and the number of queries we make to obtain
related data, execution may terminate if you happen to exceed this hourly limit. We utilize
the GraphQL GitHub API to parallelize as many queries as possible, however you need only
rerun `main.py` to pick up where you left off. All queried and preprocessed data is saved
to the `data` directory incrementally.

## More Info

More more information, see the paper and all results, located in the `results` directory.
This project was completed for the course
**CS 846: Software Analytics for Release Pipelines**,
taught by [Dr. Shane McIntosh](https://github.com/smcintosh) during the Winter 2022
term at University of Waterloo. I would like to thank him for his guidance and feedback
throughout this project, which enabled a truly challenging and rewarding experience.

