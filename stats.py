import json
import re
import git
import optparse
import os


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

    for commit in repo.heads.master.commit.iter_parents(**iter_opts):
        add(commit.author)
        add(commit.committer)
    return users


def find_users(repo, after, before):
    users = []
    heads = repo.heads
    iter_opts = {}
    if before: iter_opts['before'] = before
    if after: iter_opts['after'] = after
    for commit in repo.heads.master.commit.iter_parents(**iter_opts):
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

def print_stats_csv(data, filename):
    # Basic CSV writer
    with open(filename, 'w') as f:
        f.write('email,commits,insertions,deletions,avg_file\n')
        for user in data.keys():
            line = (
                user,
                data[user]['commits'],
                data[user]['insertions'],
                data[user]['deletions'],
                data[user]['average_files']
            )
            f.write('%s,%d,%d,%d,%.2f\n' % line)




if __name__ == '__main__':
    parser = optparse.OptionParser('Get statistics for a git repository')
    parser.add_option('-R', '--repo', dest='repo', default='gaia',
                      help='path to a git repository')
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

    if not os.path.exists(opts.repo):
        print 'The specified repository "%s" does not exist' % opts.repo
        parser.exit(1)
    repo = git.Repo(opts.repo, odbt=git.GitCmdObjectDB)
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
        data = stats(repo, users=[opts.user], after=opts.after, before=opts.before)
    else:
        data = stats(repo, after=opts.after, before=opts.before)

    print_stats_csv(data, 'output')

