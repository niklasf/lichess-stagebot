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

from slackclient import SlackClient

def sh(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT)


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

                    self.handle(args[1:])

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
        branch = "build-artifacts"
        download = "%s/lila-%s.tar.gz" % (self.config.get("s3", "bucket"), branch)
        self.send("Downloading %s ..." % download)
        urllib.urlretrieve(download, "lila.tar.gz")

        self.send("Deploying ...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SlackBot()
    if len(sys.argv) > 1:
        bot.handle(sys.argv[1:])
    else:
        bot.run()
