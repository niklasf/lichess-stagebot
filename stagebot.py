from __future__ import print_function

import os
import time
import logging

from slackclient import SlackClient

class SlackBot:
    def __init__(self, token):
        self.slack = SlackClient(token)

    def run(self):
        if not self.slack.rtm_connect():
            raise Exception("rtm connect failed")

        logging.info("Connected.")

        while True:
            for msg in self.slack.rtm_read():
                logging.debug("%s", msg)
                if msg.get("type") == "message":
                    self.handle_message(msg["text"])

            time.sleep(1)

    def send(self, message):
        logging.info(message)
        self.slack.rtm_send_message("bot-testing", message)

    def handle_message(self, message):
        if "deploy" in message and "stagebot" in message:
            self.deploy()

    def deploy(self):
        self.send("deploying ...")
        self.send("deployed (or not)")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    bot = SlackBot(os.environ["SLACK_BOT_TOKEN"])
    bot.run()
