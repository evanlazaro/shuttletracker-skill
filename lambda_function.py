import logging
import requests
import json
from datetime import datetime
import pytz
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Welcome, you can ask when the shuttle will arrive at any stop or to list all stops"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class FindETAIntentHandler(AbstractRequestHandler):
    """Handler for Find ETA Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("FindETAIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        
        stop = handler_input.request_envelope.request.intent.slots["stop"].value
        
        all_stops = requests.get('https://shuttles.rpi.edu/stops').json()

        # Extract the IDs for all stops which match the provided stop
        names_ids = [(stop['name'],stop['id']) for stop in all_stops]
        matching = [n[1] for n in names_ids if stop in n[0].lower()]
        
        if len(matching) == 0:
            res = "Stop {} is not a valid stop. Please try again.".format(stop)
            return (
                    handler_input.response_builder
                        .speak(res)
                        .ask(res)
                        .response
                )

        etas = requests.get('https://shuttles.rpi.edu/eta').json()
        
        times = []
        arriving = False
        
        # Add all ETAs for the stop into a list
        for index,eta in etas.items():
            stop_etas = eta['stop_etas']
            for arrival in stop_etas:
                if arrival['stop_id'] in matching:
                    times.append(arrival['eta'])
                    arriving = arriving or arrival['arriving']
        
        # No ETAs
        if len(times) == 0:
            message = "There are no shuttles arriving at {} in the near future".format(stop)
        # Shuttle is arriving now
        elif arriving:
            message = "A shuttle is arriving at {} right now".format(stop)
        else:
            time_diffs = []
            now = datetime.now(pytz.timezone('US/Eastern'))
            # Turn all time strings into datetime objects and append the time difference
            for time in times:
                t = datetime.strptime(time,'%Y-%m-%dT%H:%M:%S.%f%z')
                time_diffs.append(t-now)
            # Find the smallest time, and turn it into minutes (truncate seconds)
            final = min(time_diffs)
            minutes = final.seconds // 60
            # Somethings gone horribly wrong
            if final.total_seconds() < 0:
                message = "A shuttle is arriving in negative {} minutes... hmm, that doesn't seem right.".format(minutes)
            # Output the ETA
            else:
                message = "A shuttle will arrive at {} in {} minutes".format(stop,minutes)
        
        return (
            handler_input.response_builder
                .speak(message)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class ListStopsHandler(AbstractRequestHandler):
    """Handler for Listing all stops"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ListStops")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        all_stops = requests.get('https://shuttles.rpi.edu/stops').json()
        names = set([stop['name'] for stop in all_stops])

        message = "Here is a list of all stops: {}".format(", ".join(names))
        
        return (
            handler_input.response_builder
                .speak(message)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "You can say hello to me! How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(FindETAIntentHandler())
sb.add_request_handler(ListStopsHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()