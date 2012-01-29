#!/usr/bin/env python
#coding: utf-8
import json
import os
import difflib
import subfield
from datetime import datetime
from django.core.management import setup_environ

try:
    from scielomanager import settings
except ImportError:
    BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
    from sys import path
    path.append(BASE_PATH)
    import settings

setup_environ(settings)
from journalmanager.models import *

class SectionImport:

    def __init__(self):
        self._summary = {}

    def charge_summary(self, attribute):
        """
        Function: charge_summary
        Carrega com +1 cada atributo passado para o metodo, se o attributo nao existir ele e criado.
        """
        if not self._summary.has_key(attribute):
            self._summary[attribute] = 0    
        
        self._summary[attribute] += 1

    def get_summary(self):
        """
        Function: get_summary
        Retorna o resumo de carga de registros
        """
        return self._summary


    def load_section(self, record):
        section = ""
        section_by_language = {}

        if record.has_key('49'):
            for sec in record['49']: # Criando dicionário organizado de secoes
                parsed_subfields = subfield.CompositeField(subfield.expand(sec))
                if not section_by_language.has_key(parsed_subfields['c']):
                    section_by_language[parsed_subfields['c']] = {} # Criando Secao
                if not section_by_language[parsed_subfields['c']].has_key(parsed_subfields['l']):
                    section_by_language[parsed_subfields['c']][parsed_subfields['l']] = parsed_subfields['t']
        else:
            print u"Periódico "+record['35'][0]+u" não tem seções definidas"
            self.charge_summary('journals_without_sections')
    
        for sec_key,sec in section_by_language.items():
            section = Section()
            section.code = sec_key
            section.creation_date = datetime.now()
            section.save(force_insert=True)
            self.charge_summary('sections')

            for trans_key,trans in sec.items():
                translation = TranslatedData()
                translation.text = trans
                translation.language = trans_key
                translation.field = 'code'
                translation.model = 'section'
                translation.save(force_insert=True)
                section.translation.add(translation)
                self.charge_summary('translations')
            

        return section
        
    def run_import(self, json_file, collection):
        """
        Function: run_import
        Dispara processo de importacao de dados
        """

        json_parsed={} 

        if __name__ == '__main__':
            section_json_file = open(json_file,'r')
            section_json_parsed = json.loads(section_json_file.read())
        else:
            section_json_parsed = section_json_file # Para testes, carregado pelo unittest

        for record in section_json_parsed:
            loaded_section = self.load_section(record)

import_section = SectionImport()
import_result = import_section.run_import('section.json', 'Brasil')

print import_section.get_summary()