from __future__ import print_function

import os
import time
import logging
import subprocess
import tempfile

from slackclient import SlackClient

def sh(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT)

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

    def post_snippet(self, title, snippet):
        self.slack.api_call("files.upload", channels="bot-testing",
                            title=title, content=snippet or "<no output>", filetype="txt")

    def handle_message(self, message):
        if "deploy" in message and "stagebot" in message:
            self.deploy()

    def deploy(self):	
        try:
            self.send("Building stagebot-buildenv ...")
            sh(["docker", "build", "-t", "stagebot-buildenv", "."])

            with tempfile.TemporaryDirectory(prefix="stagebot") as tmpdir:
                self.send("Cloning repository ...")
                sh(["git", "clone", "/home/stagebot/lila", "--recursive", "--shared", tmpdir])

                DOCKER_RUN = ["docker", "run", "--volume", "%s:/home/builder/lila" % tmpdir, "stagebot-buildenv"]

                #self.send("Compiling ...")
                #sh(DOCKER_RUN + ["sbt", "stage"])

                self.send("Building ui ...")
                sh(DOCKER_RUN + ["./ui/build", "prod"])

                self.send("Deploying assets ...")
                sh(["rsync", "--archive", "--no-o", "--no-g", "%s/public" % tmpdir, "/home/lichess-stage"])
                sh(["chown", "-R", "lichess:lichess", "/home/lichess-stage"])
     
            self.send("Done.")
        except subprocess.CalledProcessError as err:
            logging.exception("Deploy failed")
            self.post_snippet(str(err), err.output.decode("utf-8", errors="ignore"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    bot = SlackBot(os.environ["SLACK_BOT_TOKEN"])
    bot.run()
