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
    EVAL = auto()
    PRIORITY = auto()
    SET_INTENT = auto()
    REPORT_TO_PRIORITIZE = auto()
    EVAL_PRIORITY = auto()
    CHECK_IMMINENT = auto()



class Report_Mod:
    START_KEYWORD = "start"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.sorted_reports = []
        self.current_report = None
        self.open_unprioritzed_reports = []
        self.report_to_set_priority = None
        self.report_to_set_priority_id = None

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
            self.state = State.SET_INTENT
            return [
                "Please select which action you would like to take:",
                "1. Evaluate a report",
                "2. Set status for unprioritized report"
            ]


        if self.state == State.SET_INTENT:
            m = message.content
            if m == "1":
                self.state = State.EVAL
            elif m == "2":
                self.state = State.PRIORITY



        if self.state == State.PRIORITY:
            # Check if there are any unpriotized reports
            try:
                with open("saved_report_history.json", "r") as file:
                    json_data = json.load(file)
            except:
                self.state = State.REPORT_COMPLETE
                return ["No open reports found."]

            open_unprioritzed_reports = [report for user, reports in json_data["user_reports"].items() for report in reports if report["Status"] == "Open" and report["Priority"] == "NULL"]
            open_prioritzed_reports = [report for user, reports in json_data["user_reports"].items() for report in reports if report["Status"] == "Open" and report["Priority"] != "NULL"]
            if len(open_unprioritzed_reports) == 0:
                self.state = State.REPORT_COMPLETE
                reply = "No unprioritized reports found."
                if len(open_prioritzed_reports) > 0:
                    reply += f"There are {open_prioritzed_reports} reports that have been prioritized and need evaluation."
                    reply += "Please start the evaluation process."
                return [
                    reply
                ]
            else:
                # Need to priotize reports

                ### SORT BY ID
                self.open_unprioritzed_reports = open_unprioritzed_reports
                reports_to_prioritize = "\n\n".join([
                    f"__**ID: {report['ID']} - Reason: {report['Reported Reason']}**__\n" + 
                    "\n".join([f"{key}: {value}" for key, value in report.items() if key != 'ID' and key != 'Reported Reason'])
                    for report in open_unprioritzed_reports
                ])

                self.state = State.REPORT_TO_PRIORITIZE
                reply =  "Thank you for starting the prioritization process. "
                reply += "Say `help` at any time for more information.\n\n"
                reply += "Here is a list of the current open unprioritized reports sorted by time submitted.\n"
                reply += reports_to_prioritize
                reply += "\n\nPlease provide the ID number of the report you wish to process:"
                return [reply]



        if self.state == State.REPORT_TO_PRIORITIZE:
            report_to_set = None
            for report in self.open_unprioritzed_reports:
                if report["ID"] == message.content:
                    report_to_set = report

            # if not report_to_set:
            #     # SET ERROR STATUS
            #     return ["Invalid ID. Please try again."]

            # Get report to set priority
            self.report_to_set_priority = report_to_set
            self.report_to_set_priority_id = message.content

            reply = "Does this content violate terms and conditions or require serious action?\n"
            reply += "1. Yes\n"
            reply += "2. No"

            self.state = State.EVAL_PRIORITY
            return [reply]

        if self.state == State.EVAL_PRIORITY:
            m = message.content
            if m == "2":
                # Set priority to low
                self.set_priority(self.report_to_set_priority_id, "Low")
                self.state = State.REPORT_COMPLETE
                return ["Priority set to low. Process complete."]
            elif m == "1":
                reply = "Is someone in imminent danger?\n"
                reply += "1. Yes\n"
                reply += "2. No"
                self.state = State.CHECK_IMMINENT
                return [reply]


        if self.state == State.CHECK_IMMINENT:
            m = message.content
            if m == "1":
                # Set priority to high
                self.set_priority(self.report_to_set_priority_id, "High")
                self.state = State.REPORT_COMPLETE
                return ["Priority set to high. Process complete."]
            elif m == "2":
                # Set priority to medium
                self.set_priority(self.report_to_set_priority_id, "Medium")
                self.state = State.REPORT_COMPLETE
                return ["Priority set to medium. Process complete."]




        if self.state == State.EVAL:
            # Compile a list of open reports from JSON data with sorted priorities
            try:
                with open("saved_report_history.json", "r") as file:
                    json_data = json.load(file)
            except:
                self.state = State.REPORT_COMPLETE
                return ["No open reports found."]
            
            open_reports = [report for user, reports in json_data["user_reports"].items() for report in reports if report["Status"] == "Open" and report["Priority"] != "NULL"]
            open_unprioritzed_reports = [report for user, reports in json_data["user_reports"].items() for report in reports if report["Status"] == "Open" and report["Priority"] == "NULL"]
            if len(open_reports) == 0:
                self.state = State.REPORT_COMPLETE
                reply = "No open reports found."
                if len(open_unprioritzed_reports) > 0:
                    reply += f"\nPlease start the prioritization process. There are {len(open_unprioritzed_reports)} reports that need to be prioritized."
                return [
                    reply
                ]


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
            # self.current_report = self.sorted_reports[int(message.content)]
            for report in self.sorted_reports:
                if report["ID"] == message.content:
                    self.current_report = report


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

            if self.state == State.BAN:
                reason = self.current_report["Reported Reason"]
                await self.notify_reported_user(self.current_report["Reported user ID"], self.actions[m]["Message"].format(reason))
                self.state = State.REPORT_COMPLETE
                return [
                    "User has been banned.",
                    "Reported content and moderator decisions sent to automated system as training data."
                    ]

            if self.state in (State.SUSPEND, State.REMOVE_CONTENT, State.WARN):
                reported_user = self.current_report["Reported user"]
                reason = self.current_report["Reported Reason"]

                # SEND MESSAGE TO USER: 
                await self.notify_reported_user(self.current_report["Reported user ID"], self.actions[m]["Message"].format(reason))

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
                    return [
                        "User has been notified.",
                        "Reported content and moderator decisions sent to automated system as training data."
                        ]


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
                return [
                    "Done",
                    "Reported content and moderator decisions sent to automated system as training data."
                ]
            
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
                await self.notify_reported_user(self.current_report["Reported user ID"], "You have been suspended for repeated false reporting.")
                self.state = State.REPORT_COMPLETE
                return [
                    "User has been suspended for repeated false reporting.",
                    "Reported content and moderator decisions sent to automated system as training data."
                ]
            else:
                # Warn user

                # SEND MESSAGE TO USER: "Ensure future reports are accurate to avoid action on your account."
                await self.notify_reported_user(self.current_report["Reported user ID"], "Ensure future reports are accurate to avoid action on your account.")
                self.state = State.REPORT_COMPLETE
                return [
                    "User has been warned for false reporting.",
                    "Reported content and moderator decisions sent to automated system as training data."
                ]


        if self.state == State.ESCALATE:
            m = message.content
            self.state = self.escalation_routes[m]["State"]
            to_send = f"System escalating to {self.escalation_routes[m]['Route']}"
            to_send += "\n\nReported content and moderator decisions sent to automated system as training data."
            print(to_send)
            self.state = State.REPORT_COMPLETE
            return [to_send]

        if self.state == State.BAN_OR_SUSPEND:
            m = message.content
            action = "suspended" if m == "1" else "banned"
            # SEND MESSAGE TO USER: f"Your account has been {action} as a result of {} content violations."
            reason = self.current_report["Reported Reason"]
            await self.notify_reported_user(self.current_report["Reported user ID"], f"Your account has been {action} as a result of {reason} content violations.")
            self.state = State.REPORT_COMPLETE
            return [
                f"User has been {action}.",
                "Reported content and moderator decisions sent to automated system as training data."
            ]


    def close_report(self):
        # if self.current_report:
        #     return self.current_report["ID"]
        # return None

        if not self.current_report:
            return
            
        # report_id = self.mod_reports[author_id].get_id()
        report_id = self.current_report["ID"]

        with open("saved_report_history.json", "r") as json_file:
            json_data = json.load(json_file)
        for user, reports in (json_data["user_reports"]).items():
            for report in reports:
                if report["ID"] == report_id:
                    report["Status"] = "Closed"
        with open("saved_report_history.json", "w") as json_file:
            json.dump(json_data, json_file)





    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    def set_priority(self, ID, priority):
        with open("saved_report_history.json", "r") as json_file:
            json_data = json.load(json_file)
        # Find report
        for user, reports in (json_data["user_reports"]).items():
            for report in reports:
                if report["ID"] == int(ID):
                    report["Priority"] = priority


        print(json_data)
        with open("saved_report_history.json", "w") as json_file:
            json.dump(json_data, json_file, indent=4)
    

    async def notify_reported_user(self, user_id, message):
        user = await self.client.fetch_user(user_id)
        if user:
            await user.send(message)
        else:
            print(f"Failed to find user with ID {user_id}")


