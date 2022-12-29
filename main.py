import datetime
import threading
import time
import util
from types import SimpleNamespace
from rich import print
import database
import logging
import sys
import atexit

from flask import Flask, render_template, redirect, Response
from apscheduler.schedulers.background import BackgroundScheduler
import flet as ft


def configure_loggers() -> list[None]:
    logging.basicConfig(
        format='[%(threadName)s] [%(levelname)s]'
               ' [%(filename)s] [Line %(lineno)d] %(message)s',
        handlers=[
            logging.FileHandler("farmer.log"),
            logging.StreamHandler(),
        ],
        level=logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.CRITICAL)  # disable flask logger
    logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
    logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.CRITICAL)
    logging.getLogger("selenium.webdriver.common.selenium_manager").setLevel(logging.CRITICAL)
    logging.getLogger("selenium.webdriver.common.selenium_manager").setLevel(logging.CRITICAL)
    logging.getLogger("selenium.webdriver.common.service").setLevel(logging.CRITICAL)
    logging.getLogger("httpx._client").setLevel(logging.CRITICAL)
    logging.getLogger("root").disabled = True  # flet logger


# Configure Logging
configure_loggers()

logger: logging.Logger = logging.getLogger("msrf")  # create msrf logger
config: util.Config = util.load_config("configuration.yaml")  # load config from file
logger.info("Loaded ./configuration.yaml into config SimpleNamespace")
db = database.DatabaseAccess(url=config.database_url)  # create database connection
logger.info(f"Connection to database ({config.database_url}) was successful.")

app = Flask(__name__, static_folder="./static", static_url_path="")  # init flask


@app.route("/")
def index():
    logger.info("Serving index webpage.")
    return render_template("index.html", accounts=db.read(), active_threads=[t.name for t in threading.enumerate()])


@app.route("/log")
def log():
    with open("farmer.log", "r") as file:
        return list(reversed(list(reversed(file.readlines()))[:20]))


@app.route("/exec_single_account/<account_id>")
def exec_single_account(account_id: int):
    account: util.MicrosoftAccount = [a for a in db.read() if a.id == account_id][0]
    threading.Thread(
        name=account.email,
        target=util.exec_farmer,
        kwargs={"account": account, "config": config, "db": db}
    ).start()
    return redirect("/")


@app.template_filter('strftime')
def _jinja2_filter_datetime(date: datetime.datetime) -> str:
    return date.strftime("%Y-%m-%d %H:%M")


def run_sequential_threads(accounts: list[util.MicrosoftAccount]):
    for account in accounts:  # loop over given accounts
        thread = threading.Thread(  # init thread object
            name=account.email,  # name of thread is the account email
            target=util.exec_farmer,
            kwargs={"account": account, "config": config, "db": db}
        )
        thread.start()  # start thread
        # wait for 3600 seconds for the thread.
        thread.join(timeout=3600)
        # once the thread exits
        # if the thread is still running, its name will be changed to indicate that the thread is unresponsive.
        # if the thread exits, the next line does nothing.
        thread.name = f"{account.email} [hung]"


def check_then_run():
    logger.info("Checking if any accounts are ready...")
    accounts_ready = list()
    for account in db.read():
        if (datetime.datetime.now(tz=datetime.timezone.utc) - account.lastExec).total_seconds() >= \
                config.minimum_auto_rerun_delay_seconds:
            logger.info(f"{account.email} is ready.")
            accounts_ready.append(account)

        else:
            logger.info(f"{account.email} is not ready.")

    # run_sequential_threads(accounts=accounts_ready)


def get_log() -> str:
    with open("farmer.log", "r") as file:
        return "".join(list((list(reversed(file.readlines()))[:100])))


def remove_account(email):
    logger.info(f"Removing {email}")


def main_screen(page: ft.Page):
    page.window_title_bar_hidden = True
    page.window_title_bar_buttons_hidden = True
    def show_bs(e):
        bs.open = True
        bs.update()

    def bs_dismissed(e):
        logger.info("dismissed")

    def close_bs(e):
        bs.open = False
        bs.update()

    bs = ft.BottomSheet(
        ft.Container(
            ft.Column(
                [
                    ft.Text("Add Account", size=35),
                    ft.Text("Note: Ensure that the Microsoft Rewards onboarding tasks have been completed. Make sure "
                            "the credentials are correct.", italic=True, color=ft.colors.BLUE_GREY),
                    ft.Row(
                        [
                            ft.TextField(label="Email"),
                            ft.TextField(label="Password"),
                            ft.ElevatedButton("Add", on_click=close_bs)
                        ],

                    )
                ],
                tight=True,
            ),
            padding=10,
        ),
        open=False,
        on_dismiss=bs_dismissed,
    )
    page.overlay.append(bs)

    page.title = "Microsoft Rewards Farmer"
    page.window_height = 720
    page.window_width = 1280
    page.window_resizable = False

    log_text = ft.Text(get_log(), font_family="Consolas", size=10, overflow=ft.TextOverflow.VISIBLE)
    accountsTable = ft.DataTable(
        width=600 if not page.web else 800,
        columns=[
            ft.DataColumn(ft.Text("Account")),
            ft.DataColumn(ft.Text("Last Exec")),
            ft.DataColumn(ft.Text("Points"), numeric=True),
            ft.DataColumn(ft.Text("")),
        ],
        rows=[
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(account.email)),
                    ft.DataCell(
                        ft.Text(
                            f"{(((datetime.datetime.now(tz=datetime.timezone.utc) - account.lastExec).total_seconds() / 60) / 60):.0f} hrs ago")),
                    ft.DataCell(ft.Text(str(account.points))),
                    ft.DataCell(
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            tooltip="Remove Account",
                            on_click=lambda e: [remove_account(e.control.data), hydrate()],
                            data=account.email
                        )
                    )
                ]

            ) for account in db.read()
        ],
    )
    page.add(
        ft.Row(
            [
                ft.WindowDragArea(
                    ft.Container(ft.Text("Microsoft Rewards Farmer"),
                                 bgcolor=ft.colors.TRANSPARENT, padding=10, margin=0), expand=True
                ),
                ft.IconButton(ft.icons.MINIMIZE, on_click=lambda _: page.window_close()),
            ],
            visible=not page.web,
        ),
        ft.Row(
            [
                ft.Column(
                    controls=[
                        ft.Container(
                            alignment=ft.alignment.center,
                            content=accountsTable,
                            expand=True,
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.icons.ADD,
                                    tooltip="Add Account",
                                    on_click=show_bs
                                ),
                            ]
                        )
                    ],

                ),
                ft.VerticalDivider(),
                ft.Column(
                    expand=True,
                    controls=[log_text],
                    scroll=ft.ScrollMode.ALWAYS,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    def hydrate():
        accountsTable.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(account.email)),
                    ft.DataCell(
                        ft.Text(
                            f"{(((datetime.datetime.now(tz=datetime.timezone.utc) - account.lastExec).total_seconds() / 60) / 60):.0f} hrs ago")),
                    ft.DataCell(ft.Text(str(account.points))),
                    ft.DataCell(
                        ft.IconButton(
                            icon=ft.icons.CLOSE,
                            tooltip="Remove Account",
                            on_click=lambda e: [remove_account(e.control.data), hydrate()],
                            data=account.email
                        )
                    )
                ]

            ) for account in db.read()
        ]

        log_text.value = get_log()
        page.update()

    while True:
        time.sleep(20)
        hydrate()


if __name__ == '__main__':
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=check_then_run, trigger="interval", seconds=20)
    # scheduler.start()
    # app.run(debug=not config.debug)
    # atexit.register(lambda: scheduler.shutdown())

    # for account in db.read():
    #     util.exec_farmer(
    #         account=account,
    #         config=config,
    #         db=db
    #     )

    ft.app(target=main_screen, view=ft.WEB_BROWSER)

# PB PASSWORD C!ddKm9R5ESTJJz6
#
"""

let vars = []

for (var b in window){
	if (window.hasOwnProperty(b)){
	vars.push(b)
{
}

vars.sort()
console.log(vars)

"""
