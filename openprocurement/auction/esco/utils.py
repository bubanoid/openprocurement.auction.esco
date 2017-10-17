# -*- coding: utf-8 -*-
import decimal
import simplejson
import couchdb.json
from couchdb import util
from barbecue import chef
from decimal import Decimal

def prepare_initial_bid_stage(bidder_name="",
                              bidder_id="",
                              time="",
                              amount_features="",
                              coeficient="",
                              amount="",
                              annualCostsReduction=None,
                              yearlyPaymentsPercentage="",
                              contractDurationDays="",
                              contractDurationYears=""):
    if annualCostsReduction is None:
        annualCostsReduction = []
    stage = dict(bidder_id=bidder_id, time=str(time))
    stage["label"] = dict(
        en="Bidder #{}".format(bidder_name),
        uk="Учасник №{}".format(bidder_name),
        ru="Участник №{}".format(bidder_name)
    )
    stage['amount'] = amount if amount else 0
    stage['yearlyPaymentsPercentage'] = yearlyPaymentsPercentage if yearlyPaymentsPercentage else 0
    stage['contractDurationDays'] = contractDurationDays if contractDurationDays else 0
    stage['contractDurationYears'] = contractDurationYears if contractDurationYears else 0
    stage['annualCostsReduction'] = annualCostsReduction
    if amount_features is not None and amount_features != "":
        stage['amount_features'] = str(amount_features)
    if coeficient:
        stage['coeficient'] = str(coeficient)
    return stage


def prepare_results_stage(bidder_name="",
                              bidder_id="",
                              time="",
                              amount_features="",
                              coeficient="",
                              amount="",
                              yearlyPaymentsPercentage="",
                              contractDurationDays="",
                              contractDurationYears=""):
    stage = dict(bidder_id=bidder_id, time=str(time))
    stage["label"] = dict(
        en="Bidder #{}".format(bidder_name),
        uk="Учасник №{}".format(bidder_name),
        ru="Участник №{}".format(bidder_name)
    )
    stage['amount'] = amount if amount else 0
    stage['yearlyPaymentsPercentage'] = yearlyPaymentsPercentage if yearlyPaymentsPercentage else 0
    stage['contractDurationDays'] = contractDurationDays if contractDurationDays else 0
    stage['contractDurationYears'] = contractDurationYears if contractDurationYears else 0
    if amount_features is not None and amount_features != "":
        stage['amount_features'] = str(amount_features)
    if coeficient:
        stage['coeficient'] = str(coeficient)
    return stage


def prepare_bids_stage(exist_stage_params, params={}):
    exist_stage_params.update(params)
    stage = dict(type="bids", bidder_id=exist_stage_params['bidder_id'],
                 start=str(exist_stage_params['start']), time=str(exist_stage_params['time']))
    stage["amount"] = exist_stage_params['amount'] if exist_stage_params['amount'] else 0
    stage["yearlyPaymentsPercentage"] = exist_stage_params['yearlyPaymentsPercentage'] if exist_stage_params['yearlyPaymentsPercentage'] else 0
    stage["contractDurationDays"] = exist_stage_params['contractDurationDays'] if exist_stage_params['contractDurationDays'] else 0
    stage["contractDurationYears"] = exist_stage_params['contractDurationYears'] if exist_stage_params['contractDurationYears'] else 0
    if 'amount_features' in exist_stage_params:
        stage["amount_features"] = exist_stage_params['amount_features']
    if 'coeficient' in exist_stage_params:
        stage["coeficient"] = exist_stage_params['coeficient']

    if exist_stage_params['bidder_name']:
        stage["label"] = {
            "en": "Bidder #{}".format(exist_stage_params['bidder_name']),
            "ru": "Участник №{}".format(exist_stage_params['bidder_name']),
            "uk": "Учасник №{}".format(exist_stage_params['bidder_name'])
        }
    else:
        stage["label"] = {
            "en": "",
            "ru": "",
            "uk": ""
        }
    return stage

def sorting_start_bids_by_amount(bids, features=None, reverse=True):
    """
    >>> from json import load
    >>> import os
    >>> data = load(open(os.path.join(os.path.dirname(__file__),
    ...                               'tests/functional/data/tender_simple.json')))
    >>> sorted_data = sorting_start_bids_by_amount(data['data']['bids'])

    """
    def get_amount(item):
        return item['value']['amountPerformance']

    # return sorted(bids, key=get_amount, reverse=reverse)
    return chef(bids, features=features, awarding_criteria_key="amountPerformance")


def to_decimal(fraction):
    return Decimal(fraction.numerator) / Decimal(fraction.denominator)

def couchdb_json_decode():
    my_encode = lambda obj, dumps=simplejson.dumps: dumps(obj, allow_nan=False, ensure_ascii=False)

    def my_decode(string_):

        if isinstance(string_, util.btype):
            string_ = string_.decode("utf-8")
        return simplejson.loads(string_, parse_float=decimal.Decimal)

    couchdb.json.use(decode=my_decode, encode=my_encode)
