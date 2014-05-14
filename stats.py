import json
import re
import git
import optparse
import os
import csv
import copy


def build_email_directory(repo, after, before):
    users = {}
    heads = repo.heads
    iter_opts = {}
    if before: iter_opts['before'] = before
    if after: iter_opts['after'] = after
    def add(actor):
        if users.has_key(actor.email):
            if not actor.name in users[actor.email]:
                users[actor.email].append(actor.name)
        else:
            users[actor.email] = [actor.name]

    for commit in repo.head.commit.iter_parents(**iter_opts):
        add(commit.author)
        add(commit.committer)
    return users


def find_users(repo, after, before):
    users = []
    heads = repo.heads
    iter_opts = {}
    if before: iter_opts['before'] = before
    if after: iter_opts['after'] = after
    for commit in repo.head.commit.iter_parents(**iter_opts):
        if not commit.author.email in users:
            users.append(commit.author.email)
        if not commit.committer.email in users:
            users.append(commit.committer.email)
    return users


def find_commits(repo, email, after, before):
    relevant_commits = {
        'author': [],
        'committer_not_author': [],
    }
    iter_opts = {}
    if before: iter_opts['before'] = before
    if after: iter_opts['after'] = after
    # Find interesting commits
    for commit in repo.head.commit.iter_parents(**iter_opts):
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


def stats_for_user(repo, email, after, before):
    data = {
        'insertions': 0,
        'deletions': 0,
        'commits': 0,
    }
    files_touched = 0
    commits = find_commits(repo, email, after, before)
    for commit in commits['author']:
        data['insertions'] += commit.stats.total['insertions']
        data['deletions'] += commit.stats.total['deletions']
        data['commits'] += 1
        files_touched += commit.stats.total['files']
    if data['commits'] > 0:
        data['average_files'] = files_touched / data['commits']
    return data


def stats(repo, users='*', after=None, before=None):
    if users == '*':
        print 'Finding all users'
        users = find_users(repo, after, before)
    else:
        print 'Finding commits for %d users' % len(users)
    print 'Found %d users' % len(users)
    data = {}
    for user in users:
        print 'Finding stats for %s' % user
        data[user] = stats_for_user(repo, user, after, before)
        print 'Found stats for %d commits authored by %s' % (data[user]['commits'], user)
    return data

def print_stats_csv(repo, data, filename, after, before):
    with open(filename, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Email', 'Commits', 'Insertions', 'Deletions', 'Average Files Changed'])
        for user in data.keys():
            line = [
                user,
                data[user]['commits'],
                data[user]['insertions'],
                data[user]['deletions'],
                data[user]['average_files']
            ]
            writer.writerow(line)
        totals = total_stats(data)
        writer.writerow([
            'TOTAL',
            totals['commits'],
            totals['insertions'],
            totals['deletions'],
            totals['average_files']
        ])


def add_users(userA, userB):
    r = {}
    for i in ('commits', 'insertions', 'deletions', 'average_files'):
        r[i] = userA[i] + userB[i]
    r['average_files'] = ((userA['commits'] * userA['average_files']) + (userB['commits'] * userB['average_files'])) / (userA['commits'] + userB['commits'])
    return r

def total_stats(stats):
    totals = {
        'insertions': 0,
        'deletions': 0,
        'commits': 0,
        'average_files': 0
    }
    for user in stats.keys():
        totals = add_users(totals, stats[user])
    return totals

def add_stats(statsA, statsB):
    result = copy.deepcopy(statsA)
    for keyB in statsB.keys():
        if result.has_key(keyB):
            results[keyB] = add_users(statsA[keyB], statsB[keyB])
        else:
            result[keyB] = statsB[keyB]


if __name__ == '__main__':
    parser = optparse.OptionParser('Get statistics for a git repository')
    parser.add_option('--since', '--after', dest='after', default=None,
                      help='string to pass on to git\'s --after param')
    parser.add_option('--until', '--before', dest='before', default=None,
                      help='string to pass on to git\'s --before param')
    parser.add_option('-u', '--user', dest='user', default=None,
                      help='optionally only grab stats for one user')
    parser.add_option('--user-file', dest='user_file', default=None,
                      help='json file that contains a list of email addresses')
    parser.add_option('--build-user-directory', dest='build_user_dir',
                       action='store_true', default=False,
                       help='build a directory of emails to names used')
    opts, args = parser.parse_args()

    for arg in args:
        if not os.path.exists(arg):
            print 'The specified repository "%s" does not exist' % opts.repo
            parser.exit(1)
        repo = git.Repo(arg, odbt=git.GitCmdObjectDB)
        assert repo.bare == False

    if opts.build_user_dir:
        users = build_email_directory(repo, opts.after, opts.before)
        print json.dumps(users, indent=2)
        parser.exit(0)

    if opts.user and opts.user_file:
        print 'You must specify either a user name or a user name file, not both'
        parser.exit(1)

    if opts.user_file:
        if not os.path.exists(opts.user_file):
            print 'User file is missing'
            parser.exit(1)
        try:
            with open(opts.user_file) as f:
                user_list = json.load(f)
        except:
            print 'Malformed user list json'
            parser.exit(1)
        data = stats(repo, users=user_list, after=opts.after, before=opts.before)
    elif opts.user:
        user_list = [opts.user]
    else:
        user_list = '*'
    data = stats(repo, users=user_list, after=opts.after, before=opts.before)



    print_stats_csv(repo, data, 'output.csv', opts.after, opts.before)

