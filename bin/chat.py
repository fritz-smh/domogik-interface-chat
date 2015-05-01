#!/usr/bin/python
# -*- coding: utf-8 -*-

""" This file is part of B{Domogik} project (U{http://www.domogik.org}).

License
=======

B{Domogik} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Domogik} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Plugin purpose
==============

Chat

Implements
==========

- ChatManager

@author: Fritz <fritz.smh@gmail.com>
@copyright: (C) 2007-2015 Domogik project
@license: GPL(v3)
@organization: Domogik
"""

from domogik.interface.common.interface import Interface
from domogik_packages.interface_chat.lib import npyscreen
from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage


from zmq.eventloop.ioloop import IOLoop
import zmq

from argparse import ArgumentParser
import threading
import traceback
import time
import sys
import curses


WELCOME_MESSAGE = ["Welcome in the Butler chat!",
                   "With this interface you can speak with your Domogik Butler!",
                   "",
                   "You just need to press the tabulation key to move in the input field and start typing.",
                   "To quit, just say 'quit'",
                   "",
                   "Enjoy ;)",
                   ""]

class ChatManager(Interface):
    """ Chat with the butler
    """

    def __init__(self):
        """ Init plugin
        """
        ### Option parser
        parser = ArgumentParser()
        parser.add_argument("-l", 
                          action="store_true", 
                          dest="light_mode", 
                          default=False, \
                          help="Start the chat interface in a very basic and light mode.")

        Interface.__init__(self, name='chat', daemonize = False, log_on_stdout = False, parser = parser)

        # check if the client is configured. If not, this will stop the client and log an error
        #if not self.check_configured():
        #    return

        ### Start the chat client 
        self.log.info(u"Start the chat client...")
        thr_chat = threading.Thread(None,
                                   self.run_chat,
                                   'bot',
                                   (),
                                   {})
        thr_chat.start()

        self.log.info(u"Interface ready :)")
        self.ready()
        print(u"Bye :)")
        self.force_leave()

    def process_response(self, response):
        """ Process the butler response
        """
        # filter for this client only
        if response['reply_to'] != self.source:
            return

        # process
        try:
            if self.options.light_mode:
                print(u"Butler > {0}".format(response['text']))
            else:
                self.chat_app.add_response(u"{0}".format(response['text']))
        except:
            self.log.error(u"Error when processing response : {0}".format(traceback.format_exc()))
            if self.options.light_mode:
                print(u"Error when processing response : {0}".format(traceback.format_exc()))
            else:
                self.chat_app.add_response(u"Error : {0}".format(traceback.format_exc()))

    def run_chat(self):
        """ chat interface
        """
        if self.options.light_mode:
            time.sleep(1)
            while True:
                msg = raw_input("")
                self.send_to_butler(u"{0}".format(msg), identity = "cli user", media = "chat", location = None, mood = None)

        else:
            self.chat_app = Chat()
            self.chat_app.set_butler_callback(self.send_to_butler)
            self.chat_app.run()




class ActionControllerChat(npyscreen.ActionControllerSimple):
    def create(self):
        self.add_action(u'^.*', self.send_to_butler, False)

    def send_to_butler(self, command_line, widget_proxy, live):
        you = u"You > {0}".format(command_line)
        self.parent.value.set_values(self.parent.value.get() + [you])
        self.parent.wMain.values = self.parent.value.get()
        self.parent.wMain.display()

        # handle special commands
        if command_line.lower() == "quit":
            IOLoop.instance().stop()
            sys.exit(0)  # why is this needed ?

        elif command_line.lower() == "reload":
            try:
                cli = MQSyncReq(zmq.Context())
                msg = MQMessage()
                msg.set_action('butler.reload.do')
                result = cli.request('butler', msg.get(), timeout=10).get()
                if result:
                    msg = "*** action reload : {0}".format(result)
                    self.parent.value.set_values(self.parent.value.get() + [msg])
            except:
                msg = u"*** action reload : error (is butler component ok ?)"
                self.parent.value.set_values(self.parent.value.get() + [msg])

        # handle butler
        else:
            self.parent.butler_cb(command_line, identity = "cli user", media = "chat", location = None, mood = None)

        self.parent.wMain.values = self.parent.value.get()
        self.parent.wMain.display()


#class FmSpeak(npyscreen.FormMuttActiveTraditional):
class FmSpeak(npyscreen.FormMuttActive):
    ACTION_CONTROLLER = ActionControllerChat

class Chat(npyscreen.NPSApp):
    def set_butler_callback(self, cb):
        self.butler_cb = cb

    def leave(self, cr):
        IOLoop.instance().stop()
        sys.exit(cr)  # why is this needed ?

    def add_response(self, data):
        butler = u"Butler > {0}".format(data)
        self.F.value.set_values(self.F.value.get() + [butler])
        self.F.wMain.values = self.F.value.get()
        self.F.wMain.display()
        
    def main(self):
        self.F = FmSpeak()
        del self.F.wMain.handlers[ord('l')] #remove 'l' as find
        self.F.wMain.handlers.update({"^Q": self.leave}) #add CTRL-F
        self.F.wStatus1.value = u"Chat history"
        self.F.wStatus2.value = u"Input"
        self.F.value.set_values(WELCOME_MESSAGE)
        self.F.wMain.values = self.F.value.get()
        self.F.butler_cb = self.butler_cb
        self.F.edit()





if __name__ == "__main__":
    chat = ChatManager()
