from enum import Enum, auto
import discord
import re
import json
import os

class State(Enum):
    REPORT_START = auto()
    ACTION_SELECTED = auto()
    REPORT_SELECTED = auto()
    REPORT_COMPLETE = auto()
    ESCALATE = auto()
    BAN = auto()
    SUSPEND = auto()
    REMOVE_CONTENT = auto()
    WARN = auto()
    DISMISS = auto()
    SECONDARY_MODERATOR = auto()
    SCAM_ACTIVITY_TEAM = auto()
    TERRORIST_ACTIVITY_TEAM = auto()
    USER_SAFETY_TEAM = auto()
    CHECK_FALSE = auto()
    BAN_OR_SUSPEND = auto()



class Report_Mod:
    START_KEYWORD = "eval"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.sorted_reports = []
        self.current_report = None

        self.actions = {
            "1": {
                "Action": "Escalate report",
                "State": State.ESCALATE,
            },
            "2": {
                "Action": "Ban offending user",
                "State": State.BAN,
                "Message": "Your account has been banned as a result of {} content violations."
            },
            "3": {   
                "Action": "Suspend offending user",
                "State": State.SUSPEND,
                "Message": "Your account has been suspended as a result of {} content violations."
            },
            "4": {
                "Action": "Remove content",
                "State": State.REMOVE_CONTENT,
                "Message": "Your content has been removed as a result of {} content violations."
            },
            "5": {
                "Action": "Warn offending user",
                "State": State.WARN,
                "Message": "Ensure {} to avoid action on your account."
            },
            "6": {
                "Action": "Dismiss report",
                "State": State.DISMISS,
            }
        }


        self.escalation_routes = {
            "1": {"Route": "Secondary moderator", "State": State.SECONDARY_MODERATOR},
            "2": {"Route": "Scam activity team", "State": State.SCAM_ACTIVITY_TEAM},
            "3": {"Route": "Terrorist activity team", "State": State.TERRORIST_ACTIVITY_TEAM},
            "4": {"Route": "User safety team", "State": State.USER_SAFETY_TEAM}
        }



    async def handle_message(self, message):

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            # Compile a list of open reports from JSON data with sorted priorities
            try:
                with open("saved_report_history.json", "r") as file:
                    json_data = json.load(file)
            except:
                self.state = State.REPORT_COMPLETE
                return ["No open reports found."]
            open_reports = [report for user, reports in json_data["user_reports"].items() for report in reports if report["Status"] == "Open"]
            priority_order = {"High": 1, "Medium": 2, "Low": 3}
            open_reports_sorted = sorted(open_reports, key=lambda x: (priority_order.get(x["Priority"], 4), x["ID"]))
            self.sorted_reports = open_reports_sorted
            open_reports_sorted_str = "\n\n".join([
                f"__**ID: {report['ID']} - Priority: {report['Priority']}**__\n" + 
                "\n".join([f"{key}: {value}" for key, value in report.items() if key != 'ID' and key != 'Priority'])
                for report in open_reports_sorted
            ])
            
            self.state = State.REPORT_SELECTED

            reply =  "Thank you for starting the evaluation process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Here is a list of the current open reports sorted by priority.\n"
            reply += open_reports_sorted_str
            reply += "\n\nPlease provide the ID number of the report you wish to process:"
            return [reply]
        
        if self.state == State.REPORT_SELECTED:
            # Need to ensure respond with number in range

            # Get report
            self.current_report = self.sorted_reports[int(message.content)]
            self.state = State.ACTION_SELECTED
            # Record message details
            reasons = "\n".join([f"{key}. {value['Action']}" for key, value in self.actions.items()])
            return [
                "Select action(s) to be taken:\n",
                reasons
            ]

        if self.state == State.ACTION_SELECTED:
            m = message.content
            self.state = self.actions[m]["State"]
            if self.state == State.ESCALATE:
                reasons = "\n".join([f"{key}. {value['Route']}" for key, value in self.escalation_routes.items()])
                return [
                    "Select route to escalate to:\n",
                    reasons
                ]

            if self.state in (State.BAN, State.SUSPEND, State.REMOVE_CONTENT, State.WARN):
                reported_user = self.current_report["Reported user"]

                # SEND MESSAGE TO USER: [self.actions[m]["Message"].format(report["Reported user"])]

                # Get number of reports on user
                with open("saved_report_history.json", "r") as file:
                    json_data = json.load(file)

                reports = json_data["user_reports"][reported_user]

                if len(reports) >= 3:
                    self.state = State.BAN_OR_SUSPEND
                    reply = f"User has a total of {len(reports)} reports filed against them.\n"
                    reply += "Please choose to either:\n"
                    reply += "1. Suspend offending user\n"
                    reply += "2. Ban offending user"
                    return [reply]
                else:
                    self.state = State.REPORT_COMPLETE
                    return ["User has been notified"]


            if self.state == State.DISMISS:
                self.state = State.CHECK_FALSE
                reply = "Was it a false report?\n"
                reply += "1. Yes\n"
                reply += "2. No"
                return [reply]
            

        if self.state == State.CHECK_FALSE:
            m = message.content
            if m == "2":
                self.state = State.REPORT_COMPLETE
                return ["Done"]
            
            # NEED TO KEEP TRACK OF FALSE REPORTS BY USERS
            if os.path.isfile("saved_false_reports.json"):
                with open("saved_false_reports.json", "r") as json_file:
                    json_data = json.load(json_file)
            else:
                with open("saved_false_reports.json", "w") as json_file:
                    json.dump({}, json_file)
                    json_data = {}
            
            if self.current_report["Reported by"] in json_data:
                json_data[self.current_report["Reported by"]] += 1
            else:
                json_data[self.current_report["Reported by"]] = 1

            with open("saved_false_reports.json", "w") as json_file:
                json.dump(json_data, json_file, indent=4)



            if json_data[self.current_report["Reported by"]] >= 3:
                # Suspend user
                
                # SEND MESSAGE TO USER: "You have been suspended for repeated false reporting."
                self.state = State.REPORT_COMPLETE
                return ["User has been suspended for repeated false reporting."]
            else:
                # Warn user

                # SEND MESSAGE TO USER: "Ensure future reports are accurate to avoid action on your account."
                self.state = State.REPORT_COMPLETE
                return ["User has been warned for false reporting"]

            




        if self.state == State.ESCALATE:
            m = message.content
            self.state = self.escalation_routes[m]["State"]
            to_send = f"System escalating to {self.escalation_routes[m]['Route']}"
            print(to_send)
            self.state = State.REPORT_COMPLETE
            return [to_send]




        if self.state == State.BAN_OR_SUSPEND:
            m = message.content
            action = "suspended" if m == "1" else "banned"
            # SEND MESSAGE TO USER: f"Your account has been {action} as a result of {} content violations."
            self.state = State.REPORT_COMPLETE
            return [f"User has been {action}"]



    def get_id(self):
        return self.current_report["ID"]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    

