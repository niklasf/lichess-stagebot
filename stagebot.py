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

                if msg.get("type") == "message":
                    args = msg["text"].split()
                    if args[0].lower() not in ["stagebot", "@stagebot"]:
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

        if args.command == "echo":
            self.send("echo")
        elif args.command == "deploy":
            self.deploy(args)

    def deploy(self, args):
        download = "%s/lila-%s.tar.gz" % (self.config.get("s3", "bucket"), args.branch)
        self.send("Downloading %s ..." % download)
        urllib.urlretrieve(download, "lila.tar.gz")

        with tarfile.open("lila.tar.gz") as tar:
            with tar.extractfile("commit.txt") as commit_file:
                sha, message = commit_file.readline().decode("utf-8").strip().split(None, 1)

            self.send("Deploying https://github.com/%s/commit/%s (`%s`) ..." % (
                self.config.get("github", "slug"), sha, message))

            app_files = [t for t in tar.getmembers() if make_relative("target/universal/stage/", t)]
            tar.extractall(self.config.get("deploy", "app"), members=app_files)

            asset_files = [t for t in tar.getmembers() if make_relative("public/", t)]
            tar.extractall(self.config.get("deploy", "assets"), members=asset_files)

        sh(self.config.get("deploy", "after"))

        self.send(":white_check_mark: Done")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SlackBot()
    if len(sys.argv) > 1:
        bot.handle(sys.argv[1:])
    else:
        bot.run()
