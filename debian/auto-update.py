import configparser
import subprocess
import datetime
import requests
import shlex

SEPARATOR1 = "-" * 100
SEPARATOR2 = "=" * 125
CFG_FILE = "auto-update.ini"

config = configparser.ConfigParser()
config.read(CFG_FILE)

log_file_path = config["PATHS"]["log_file"]
healthcheck_url = config["SERVER"]["healthcheck"]


def now():
    return f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def execute_command(command, step, step_count):
    log_str = f"[{now()}] ({step}/{step_count}) Running '{command}'.\n" + SEPARATOR1

    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
    stdout, stderr = process.communicate()
    return_code = process.poll()

    if return_code != 0:
        log_str += "\n" + stderr + "\n" + SEPARATOR1
        log_str += f"\n[{now()}] Error wile running '{command}'!\n" + "Aborting...\n"

        with open(log_file_path, "a") as log_file:
            log_file.write(log_str)

        raise Exception(f"'{command}' failed with following error(s): \n{log_str}")

    log_str += "\n" + stdout + "\n" + SEPARATOR1
    log_str += f"\n[{now()}] Finished running {command}.\n"
    return log_str


if __name__ == "__main__":

    log_str = SEPARATOR2

    try:
        log_str += f"\n[{now()}] Starting auto-update.\n"
        # Starting auto-update job & healthcheck timer
        try:
            requests.get(healthcheck_url + "/start", timeout=5)
            log_str += f"[{now()}] Sent start signal to healthcheck service.\n"
        except requests.exceptions.RequestException:
            # If the network request fails for any reason, the job isn't prevented from running
            log_str += f"[{now()}] Failed to contact healthcheck service.\n"

        commands = config["COMMANDS"]
        log_str += execute_command(commands["run_update"], 1, 4)
        log_str += execute_command(commands["run_upgrade"], 2, 4)
        log_str += execute_command(commands["run_auto-remove"], 3, 4)
        log_str += execute_command(commands["run_clean"], 4, 4)

        # Signal successful job execution:
        try:
            requests.get(healthcheck_url, data=log_str.encode("UTF-8"))
            log_str += f"[{now()}] Sent success signal to healthcheck service.\n"
        except requests.exceptions.RequestException:
            log_str += f"[{now()}] Failed to contact healthcheck service.\n"

        log_str += f"[{now()}] Auto-update successful.\n"

        with open(log_file_path, "a") as logfile:
            logfile.write(log_str)

    except Exception:
        fail_log = f"[{now()}] Auto-update failed.\n"

        try:
            requests.get(healthcheck_url + "/fail", data=log_str.encode("UTF-8"))
            fail_log += f"[{now()}] Sent fail signal to healthcheck service.\n"
        except requests.exceptions.RequestException:
            fail_log += f"[{now()}] Failed to contact healthcheck service.\n"

        with open(log_file_path, "a") as logfile:
            logfile.write(fail_log)
