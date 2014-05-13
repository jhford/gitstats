import json
import re
import git


def find_users(repo, since, before):
    users = []
    heads = repo.heads
    iter_opts = {
        'since': since,
        'before': before
    }
    for commit in repo.heads.master.commit.iter_parents(**iter_opts):
        if not commit.author.email in users:
            users.append(commit.author.email)
        if not commit.committer.email in users:
            users.append(commit.committer.email)
    return users


def find_commits(repo, email, since, before):
    relevant_commits = {
        'author': [],
        'committer_not_author': [],
    }
    iter_opts = {
        'since': since,
        'before': before
    }

    # Find interesting commits
    for commit in repo.heads.master.commit.iter_parents(**iter_opts):
        # We don't want to count merge commits because the person
        # who merges the code is irrelevant here and might double
        # count the stats
        if len(commit.parents) > 1:
            continue
        if commit.author.email == email:
            relevant_commits['author'].append(commit)
        elif commit.committer.email == email:
            relevant_commits['committer_not_author'].append(commit)

    return relevant_commits


def stats_for_user(repo, email, since, before):
    data = {
        'insertions': 0,
        'deletions': 0,
        'commits': 0,
    }
    files_touched = 0
    commits = find_commits(repo, email, since, before)
    for commit in commits['author']:
        data['insertions'] += commit.stats.total['insertions']
        data['deletions'] += commit.stats.total['deletions']
        data['commits'] += 1
    if data['commits'] > 0:
        data['average_files'] = files_touched / data['commits']
    return data


def stats_for_all(repo, since, before):
    print 'Finding all users'
    users = find_users(repo, since, before)
    print 'Found %d users' % len(users)
    data = {}
    for user in users:
        print 'Finding stats for %s' % user
        data[user] = stats_for_user(repo, user, since, before)
        print 'Found stats for %d commits authored by %s' % (data[user]['commits'], user)
    return data


if __name__ == '__main__':
    repo = git.Repo('gaia', odbt=git.GitCmdObjectDB)
    assert repo.bare == False
    #data = stats_for_all(repo, since='2013-01-01', before='2014-01-01')
    data = stats_for_user(repo, email='john@johnford.info', since='2013-01-01', before='2014-01-01')
    print json.dumps(data, indent=2)
