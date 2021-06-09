Twitch Downloader change log
============================

1.16.0 (2021-06-09)
-------------------

* Fix clips download caused by Twitch changes (#64, thanks to all participants)


1.15.0 (2021-02-15)
-------------------

* Add support for new format of clip slug (thanks @Loveangel1337)

1.14.1 (2021-01-14)
-------------------

* Handle videos which don't exist more gracefully

1.14.0 (2021-01-14)
-------------------

* Added `info` command for displaying video or clip info (#51)
* Don't show there are more videos when there aren't (#52, thanks @scottyallen)
* Fixed Twitch regression for getting the access token (#53)

1.13.1 (2020-11-23)
-------------------

* Fixed clip download issue (#45)

1.13.0 (2020-11-10)
-------------------

* Added `clips` command for listing and batch downloading clips (#26)

1.12.1 (2020-09-29)
-------------------

* Fix bug introduced in previous version which broke joining

1.12.0 (2020-09-29)
-------------------

* Added `source` as alias for best available quality (#33)
* Added `--no-join` option to `download` to skip ffmpeg join (#36)
* Added `--overwrite` option to `download` to overwrite target without prompting
  for confirmation (#37)
* Added `--pager` option to `videos`, don't page by default (#30)

1.11.0 (2020-09-03)
-------------------

* Make downloading more robust, fixes issues with some VODs (#35)
* Bundle twitch-dl to a standalone archive, simplifying installation, see
  installation instructions in README

1.10.2 (2020-08-11)
-------------------

* Fix version number displayed by `twitch-dl --version` (#29)

1.10.1 (2020-08-09)
-------------------

* Fix videos incorrectly identified as clips (#28)
* Make download command work with video URLs lacking "www" before "twitch.tv"
* Print an error when video or clip is not found instead of an exception trace

1.10.0 (2020-08-07)
-------------------

* Add `--quality` option to `download` command, allows specifying the video
  quality to download. In this case, twitch-dl will require no user input. (#22)
* Fix download of clips which contain numbers in their slug (#24)
* Fix URL to video displayed by `videos` command (it was missing /videos/)

1.9.0 (2020-06-10)
------------------

* **Breaking**: wrongly named `--max_workers` option changed to `--max-workers`.
  The shorthand option `-w` remains the same.
* Fix bug where `videos` command would crash if there was no game info (#21)
* Allow unicode characters in filenames, no longer strips e.g. cyrillic script

1.8.0 (2020-05-17)
------------------

* Fix videos command (#18)
* **Breaking**: `videos` command no longer takes the `--offset` parameter due to
  API changes
* Add paging to `videos` command to replace offset
* Add `--game` option to `videos` command to filter by game

1.7.0 (2020-04-25)
------------------

* Support for specifying broadcast type when listing videos (#13)

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
