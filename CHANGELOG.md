Twitch Downloader change log
============================

1.6.0 (2020-04-11)
------------------

* Support for downloading clips (#15)

1.5.1 (2020-04-11)
------------------

* Fix VOD naming issue (#12)
* Nice console output while downloading

1.5.0 (2020-04-10)
------------------

* Fix video downloads after Twitch deprecated access token access
* Don't print errors when retrying download, only if all fails

1.4.0 (2019-08-23)
------------------

* Fix usage of deprecated v3 API
* Use m3u8 lib for parsing playlists
* Add `--keep` option not preserve downloaded VODs

1.3.1 (2019-08-13)
------------------

* No changes, bumped to fix issue with pypi

1.3.0 (2019-08-13)
------------------

* Add `--sort` and `--offset` options to `videos` command, allows paging (#7)
* Show video URL in `videos` command output

1.2.0 (2019-07-05)
------------------

* Add `--format` option to `download` command for specifying the output format (#6)
* Add `--version` option for printing program version

1.1.0 (2019-06-06)
------------------

* Allow limiting download by start and end time

1.0.0 (2019-04-30)
------------------

* Initial release
