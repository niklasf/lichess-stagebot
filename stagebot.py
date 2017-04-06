#!/usr/bin/env python3

import os
import time
import logging
import subprocess
import tempfile
import configparser
import argparse

from slackclient import SlackClient

def sh(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT)


class ArgumentError(Exception):
    pass


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentError(message)


class SlackBot:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read("stagebot.ini")

        self.slack = SlackClient(self.config.get("stagebot", "slack_bot_token"))

        self.parser = ArgumentParser()
        self.parser.add_argument("command", choices=["echo"])

    def run(self):
        if not self.slack.rtm_connect():
            raise Exception("rtm connect failed")

        logging.info("Connected.")

        while True:
            for msg in self.slack.rtm_read():
                logging.debug("%s", msg)
                if msg.get("type") == "message":
                    try:
                        self.handle_message(msg["text"])
                    except subprocess.CalledProcessError as err:
                        logging.exception("Command failed")
                        self.post_snippet(str(err), err.output.decode("utf-8", errors="ignore"))

            time.sleep(1)

    def send(self, message):
        logging.info(message)
        self.slack.rtm_send_message("bot-testing", message)

    def post_snippet(self, title, snippet):
        self.slack.api_call("files.upload", channels="bot-testing",
                            title=title, content=snippet or "<no output>", filetype="txt")

    def handle_message(self, message):
        call = message.split()
        if call[0].lower() not in ["stagebot", "@stagebot"]:
            return

        try:
            args = self.parser.parse_args(call[1:])
        except ArgumentError as err:
            self.send(":interrobang: %s" % err)
            return

        if args.command == "echo":
            self.send("echo")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    SlackBot().run()
