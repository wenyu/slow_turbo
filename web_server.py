#!/usr/bin/sudo python3
import logging
import os
#logging.basicConfig(level=logging.DEBUG)
L = logging.getLogger(__name__)

from controller import Controller, setup_main_thread_function_call_queue
c = Controller()

from flask import Flask, Request, Response, jsonify, redirect
app = Flask("Slow Turbo - Nintendo Switch Joycon Robot")

@app.route("/")
def default_root():
    return redirect("/static/index.html")

@app.route("/api/status")
def status():
    return jsonify(c.get_status())

@app.route("/api/stop")
def stop():
    c.stop()
    return jsonify({
        "success": True,
        "msg": "Stop requested.",
    }), 200

@app.route("/api/start/<string:task>/<string:cond>")
def start(task, cond):
    success, result = c.start(task, cond)
    return jsonify(result)

@app.route("/api/*")
@app.after_request
def no_cache(r: Response):
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = "public, max-age=0"
    return r


def _main(queues):
    c._async_exec_queue = queues
    app.run("0.0.0.0")


if __name__ == "__main__":
    setup_main_thread_function_call_queue(_main)
