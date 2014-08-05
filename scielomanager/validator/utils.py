# coding: utf-8
import logging
import lxml
from packtools import stylechecker

logger = logging.getLogger(__name__)


class ErrorManager(object):
    _errors = []

    def add_object_error(self, error_obj=None, line='--', column='--', message='', level="ERROR"):
        if error_obj:
            line = getattr(error_obj, 'line', line)
            column = getattr(error_obj, 'column', column)
            message = getattr(error_obj, 'message', message)
            level = getattr(error_obj, 'level', level)

        error_data = {
            'line': line,
            'column': column,
            'message': message,
            'level': level,
        }
        if error_data not in self._errors:
            self._errors.append(error_data)

    def add_exception_error(self, exception_instance):
        message = exception_instance.message
        if hasattr(exception_instance, 'position'):
            line, column = exception_instance.position
        else:
            line, column = None, None
        self.add_object_error(error_obj=None, line=line, column=column, message=message)

    def add_list_of_errors(self, iterable):
        for error in iterable:
            self.add_object_error(error)

    def get_list(self):
        return self._errors

    def get_lines(self):
        result = []
        for error in self._errors:
            line = error['line']
            if line not in result and line > 0:
                result.append(line)
        return result


class StyleCheckerAnalyzer(object):
    target_input = None
    _target_data = None
    _can_be_analyzed = (False, "Can't be analyzed")
    _can_be_analyzed_as_exception = False
    _annotations = None
    _validation_errors = {'results': [], 'error_lines': [], }
    _error_manager = None

    def __init__(self, target_input):
        if not bool(target_input):
            raise ValueError("Can't analyze, target is None or empty")
        self.target_input = target_input
        try:
            self._target_data = stylechecker.XML(self.target_input)
            self._can_be_analyzed = (True, "")
        except lxml.etree.XMLSyntaxError as e:
            self._target_data = e
            self._can_be_analyzed_as_exception = True
        except IOError as e:
            self._can_be_analyzed = (False, "IOError while starting Stylechecker.XML(), please verify if the input is correct")
        except Exception as e:
            self._can_be_analyzed = (False, "Error while starting Stylechecker.XML()")

        self._error_manager = ErrorManager()

    def _validate_style(self):
        try:
            status, errors = self._target_data.validate_style()
        except Exception as e:
            self._can_be_analyzed = (False, "Can't validate style: %s", e.message)
            return False
        else:
            if not status:  # have errors
                self._error_manager.add_list_of_errors(errors)
            return True

    def _validate(self):
        try:
            status, errors = self._target_data.validate_style()
        except Exception as e:
            self._can_be_analyzed = (False, "Can't validate: %s", e.message)
            return False
        else:
            if not status:  # have errors
                self._error_manager.add_list_of_errors(errors)
            return True

    def annotate_errors(self):
        if isinstance(self._target_data, Exception):
            # self._target_data is an exception
            self._annotations = self._target_data.message
        elif self._target_data:
            try:
                self._target_data.annotate_errors()
                self._annotations = str(self._target_data)
            except Exception as e:
                 self._annotations = "Something went wrong when trying to get annotations: %s " % e.message

    def get_validation_errors(self):
        self._validation_errors['results'] = self._error_manager.get_list()
        self._validation_errors['error_lines'] = ", ".join(self._error_manager.get_lines())
        return self._validation_errors

    def analyze(self):
        results = {
            'can_be_analyzed': (False, "Can't be analyzed"),
            'annotations': None,
            'validation_errors': None,
        }
        if self._can_be_analyzed_as_exception:
            # in case of exceptions: self._target_data is the exception
            self._annotations = self._target_data.message
            self._validation_errors = self._error_manager.add_exception_error(self._target_data)
            results['can_be_analyzed'] = (True, None)
        elif self._can_be_analyzed[0]:
            # call validate and validate_style
            v_status = self._validate()
            s_status = self._validate_style()
            if self._can_be_analyzed[0] and (validate_status or validate_style_status):
                self.annotate_errors()
            results['can_be_analyzed'] = self._can_be_analyzed
        else:
            results['can_be_analyzed'] = self._can_be_analyzed

        results['annotations'] = self._annotations
        results['validation_errors'] = self.get_validation_errors()
        return results

    # def extract_errors_from_exception(self, exception_instance):
    #     """
    #     Return a dict with information about the syntax error exception
    #     """
    #     results = []
    #     error_lines = []
    #     if hasattr(exception_instance, 'position'):
    #         line, column = exception_instance.position
    #         error_data = {
    #             'line': line or '--',
    #             'column': column or '--',
    #             'message': exception_instance.message or '',
    #             'level': 'ERROR',
    #         }
    #         results.append(error_data)
    #         error_lines.append(str(line))
    #     return {
    #         'results': results,
    #         'error_lines': ", ".join(error_lines)
    #     }

    # def extract_validation_errors(self, validation_errors):
    #     """
    #     Return a dict of validation errors returned by stylechecker
    #     """
    #     # iterate over the errors and get the relevant data
    #     results = []
    #     error_lines = []  # only to simplify the line's highlights of prism.js plugin on template
    #     for error in validation_errors:
    #         error_data = {
    #             'line': error.line or '--',
    #             'column': error.column or '--',
    #             'message': error.message or '',
    #             'level': error.level_name or 'ERROR',
    #         }
    #         results.append(error_data)
    #         if error.line:
    #             error_lines.append(str(error.line))
    #     return {
    #         'results': results,
    #         'error_lines': ", ".join(error_lines)
    #     }
