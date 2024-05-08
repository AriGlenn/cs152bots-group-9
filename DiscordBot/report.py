from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()

    IMMINENT_DANGER = auto()
    FALSE_PROFILE = auto()
    SCAM_SPAM = auto()
    OFFENSIVE_CONTENT = auto()

    UNMATCH = auto()
    BLOCK = auto()

    MORE_INFO_OPTION = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.details = {}
        self.report_type_state = None
        self.type_report_dict = {
            "1": {
                "Reason": "Imminent danger",
                "State": State.IMMINENT_DANGER,
                "Prompt": "Please select the relevant danger: "
            },
            "2": {
                "Reason": "False profile",
                "State": State.FALSE_PROFILE,
                "Prompt": "Please select the type of concern: "
            },
            "3": {   
                "Reason": "Scam or spam",
                "State": State.SCAM_SPAM,
                "Prompt": "Please select the type of concern: "
            },
            "4": {
                "Reason": "Inappropriate or offensive content",
                "State": State.OFFENSIVE_CONTENT,
                "Prompt": "Please select the type(s) of concern: "
            },
            "5": {
                "Reason": "Other",
                "State": State.MORE_INFO_OPTION,
                "Prompt": "Please describe the reason for the report: "
            }
        }
        # Dictionary (state, number --> Text)
        self.prompt_dict = {
            State.IMMINENT_DANGER : [
                "Person is threatening self harm or suicide",
                "Person is threatening to harm me or others"
            ],
            State.FALSE_PROFILE : [
                "Profile is underage",
                "Profile has misrepresentations",
                "Profile uses pictures of a different person or is impersonating someone"
            ],
            State.SCAM_SPAM : [
                "Cryptocurrency scam",
                "Financial solicitation/scam",
                "Commercial or Promotional Activity",
                "Spam",
                "Other"
            ],
            State.OFFENSIVE_CONTENT : [
                "Inappropriate photos or messages",
                "Violent photos or messages",
                "Hate speech",
                "Harassment",
                "Bullying"
            ]
        }

    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                reported_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            # Record message details
            self.details["Reported user ID"] = reported_message.author.id
            self.details["Reported user"] = reported_message.author.name
            self.details["Reported by"] = message.author.name
            self.details["Status"] = "Open"
            self.details["Priority"] = "NULL"
            self.details["Message Content"] = reported_message.content
            reasons = "\n".join([f"{key}. {value['Reason']}" for key, value in self.type_report_dict.items()])
            return [
                "I found this message:",
                f"```{reported_message.author.name}: {reported_message.content}```",
                "Your report is private. Please select the reason for the report:",
                reasons
            ]

        if self.state == State.MESSAGE_IDENTIFIED:
            m = message.content
            self.details["Reported Reason"] = self.type_report_dict[m]["Reason"]
            self.report_type_state = self.type_report_dict[m]["State"]
            self.state = self.report_type_state
            prompt = self.type_report_dict[m]["Prompt"]
            if self.state == State.MORE_INFO_OPTION:
                # Other selected
                return [prompt]
            # Get options
            options = "\n".join([f"{i + 1}. {option}" for i, option in enumerate(self.prompt_dict[self.state])])
            return [
                f"{prompt}: \n{options}"
            ]

        # Prompt additional info
        if self.state in (State.IMMINENT_DANGER, State.FALSE_PROFILE, State.SCAM_SPAM, State.OFFENSIVE_CONTENT):
            return self.prompt_additional_info(message.content)

        if self.state == State.MORE_INFO_OPTION:
            self.details["Additional Information"] = message.content
            self.state = State.UNMATCH
            to_return = "Thank you for reporting. Our team will review your report and take appropriate action."
            if self.report_type_state == State.IMMINENT_DANGER:
                to_return = "Thank you for reporting. We take these reports seriously. Our team will review your report and take appropriate action. Please call 911 for all emergencies."
            return [
                to_return,
                "\n\nWould you like to unmatch this user?",
                "1. Yes",
                "2. No"
            ]

        if self.state == State.UNMATCH:
            m = message.content
            if m == "1":
                # Unmatch user
                self.details["Requested to be unmatched"] = "Yes"
                self.state = State.BLOCK
                return [
                    "Would you like to block this user?",
                    "1. Yes",
                    "2. No"
                ]
            elif m == "2":
                # Do not unmatch user
                self.details["Requested to be unmatched"] = "No"
                self.state = State.REPORT_COMPLETE
                return [
                    "Done"
                ]

        if self.state == State.BLOCK:
            m = message.content
            if m == "1":
                # Block user
                self.details["Requested to block"] = "Yes"
            elif m == "2":
                # Do not block user
                self.details["Requested to block"] = "No"
            self.state = State.REPORT_COMPLETE
            return [
                "Done"
            ]


    def prompt_additional_info(self, message):
        # Get corresponding prompt
        if self.state == State.OFFENSIVE_CONTENT:
            # Potential for more than one response
            messages = re.findall(r'\d+', message)
            self.details["Relevant danger/concern(s)"] = [self.prompt_dict[self.state][int(m) - 1] for m in messages]
        else:
            self.details["Relevant danger/concern(s)"] = self.prompt_dict[self.state][int(message) - 1]
        # Craft response
        to_return = "Additional information (optional): "
        if self.state == State.IMMINENT_DANGER:
            to_return = "If you someone you know is being impersonated, please have them also reach out to us.\n\n" + to_return
        # Update state
        self.state = State.MORE_INFO_OPTION
        return [
            to_return
        ]

    def get_details(self):
        return self.details

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    

