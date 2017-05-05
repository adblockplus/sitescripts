import os
import subprocess
import pipes

from sitescripts.utils import get_config


def hook(ui, repo, node=None, **kwargs):
    ctx = repo[node]
    commit_identifiers = ctx.bookmarks()
    if not commit_identifiers or ctx.branch() != 'default':
        commit_identifiers.append(ctx.branch())
    remote = [get_config().get('irchook', 'remote_command'),
              os.path.basename(repo.root), ','.join(commit_identifiers),
              str(ctx.user()), str(ctx), str(ctx.description())]
    remote = ' '.join(map(lambda s: pipes.quote(s), remote))

    command = ['ssh', get_config().get('irchook', 'remote_host'), remote]
    subprocess.call(command)
