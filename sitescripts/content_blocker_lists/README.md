# Content blocker lists

## Introduction

The `sitescripts.content_blocker_lists.bin` package contains scripts
used on the server side for producing our content blocker lists.
[Content blocker lists can be used by newer versions of Safari and iOS][1].

## generate_lists.py

The `generate_list.py` script wraps [abp2blocklist][2] so that we can more
conveniently produce our content blocker lists on our servers. The script
additionally wraps the lists with some metadata [as specified in issue 3176][3].

To use add the relevant configuration to your `scritescripts.ini` file. For
example:

    [content_blocker_lists]
    abp2blocklist_url=https://hg.adblockplus.org/abp2blocklist
    abp2blocklist_path=%(root)s/content_blocker_lists/abp2blocklist
    easylist_url=https://easylist-downloads.adblockplus.org/easylist_noadult.txt
    exceptionrules_url=https://easylist-downloads.adblockplus.org/exceptionrules.txt
    easylist_content_blocker_path=%(root)s/content_blocker_lists/easylist_content_blocker.json
    easylist_content_blocker_expires=4 days
    combined_content_blocker_path=%(root)s/content_blocker_lists/easylist+exceptionrules_content_blocker.json
    combined_content_blocker_expires=4 days

Then you can run the script as follows:

    python -m sitescripts.content_blocker_lists.bin.generate_lists

[1]: https://webkit.org/blog/3476/content-blockers-first-look/
[2]: https://hg.adblockplus.org/abp2blocklist/
[3]: https://issues.adblockplus.org/ticket/3176
