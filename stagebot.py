#!/usr/bin/env python3

import os
import time
import logging
import subprocess
import tempfile
import configparser
import argparse
import sys
import urllib.request as urllib
import tarfile
import re

from slackclient import SlackClient

def sh(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, shell=True)


def remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text


def make_relative(prefix, member):
    if member.name.startswith(prefix):
        member.name = member.name[len(prefix):]
        return True
    return False


class ParserError(Exception):
    pass

class ParserMessage(Exception):
    pass

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParserError(message)

    def _print_message(self, message, file=None):
        raise ParserMessage(message)


class SlackBot:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("stagebot.ini")


        self.parser = ArgumentParser()
        self.parser.add_argument("command", choices=["echo", "deploy"])
        self.parser.add_argument("--branch", default="master")

        self.slack = SlackClient(self.config.get("slack", "bot_token"))
        self._connect()

    def _connect(self):
        if not self.slack.rtm_connect():
            raise Exception("rtm connect failed")

        logging.info("Connected.")

    def run(self):
        while True:
            for msg in self.slack.rtm_read():
                logging.debug("%s", msg)

                if msg.get("type") == "message" and "text" in msg:
                    args = msg["text"].split()
                    if args[0].lower() not in ["stagebot", "@stagebot"] and self.config.get("slack", "bot_uid") not in args[0]:
                        continue

                    try:
                        self.handle(args[1:])
                    except Exception as err:
                        self.post_snippet("build failure", str(err))

            time.sleep(1)

    def send(self, message):
        logging.info(message)
        self.slack.rtm_send_message("bot-testing", message)

    def post_snippet(self, title, snippet):
        self.slack.api_call("files.upload", channels="bot-testing",
                            title=title, content=snippet or "<no output>", filetype="txt")

    def handle(self, args):
        try:
            args = self.parser.parse_args(args)
        except ParserMessage as msg:
            self.send("%s" % msg)
            return
        except ParserError as err:
            self.send(":interrobang: %s" % err)
            return

        if not re.match(r"^[A-Za-z0-9_-]+\Z", args.branch):
            self.send(":interrobang: Invalid branch name")
            return

        if args.command == "echo":
            self.send("echo")
        elif args.command == "deploy":
            self.deploy(args)

    def deploy(self, args):
        start_time = time.time()

        # 0. Pre
        sh(self.config.get("deploy", "pre"))

        # 1. Download server
        download = "%s/lila-server-%s.tar.gz" % (self.config.get("s3", "bucket"), args.branch)
        self.send("Downloading %s ..." % download)
        urllib.urlretrieve(download, "lila-server.tar.gz")

        # 2. Download assets
        download = "%s/lila-assets-%s.tar.gz" % (self.config.get("s3", "bucket"), args.branch)
        self.send("Downloading %s ..." % download)
        urllib.urlretrieve(download, "lila-assets.tar.gz")

        with tarfile.open("lila-server.tar.gz") as tar:
            # 3. Peek server
            with tar.extractfile("commit.txt") as commit_file:
                sha, message = commit_file.readline().decode("utf-8").strip().split(None, 1)

            self.send("Deploying server: https://github.com/%s/commit/%s (`%s`) ..." % (
                self.config.get("github", "slug"), sha, message))

            # 4. Extract server
            app_files = [t for t in tar.getmembers() if make_relative("target/universal/stage/", t)]
            tar.extractall(self.config.get("deploy", "app"), members=app_files)

        with tarfile.open("lila-assets.tar.gz") as tar:
            # 5. Peek assets
            with tar.extractfile("commit.txt") as commit_file:
                sha, message = commit_file.readline().decode("utf-8").strip().split(None, 1)

            self.send("Deploying assets: https://github.com/%s/commit/%s (`%s`) ..." % (
                self.config.get("github", "slug"), sha, message))

            # 6. Extract assets.
            asset_files = [t for t in tar.getmembers() if make_relative("public/", t)]
            tar.extractall(self.config.get("deploy", "assets"), members=asset_files)

        # 7. Post
        sh(self.config.get("deploy", "post"))

        end_time = time.time()
        self.send(":white_check_mark: Done in %.1fs" % (end_time - start_time))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SlackBot()
    if len(sys.argv) > 1:
        bot.handle(sys.argv[1:])
    else:
        bot.run()
