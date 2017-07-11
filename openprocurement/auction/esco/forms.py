from flask import request, session, current_app as app
from fractions import Fraction
from wtforms import Form, DecimalField, StringField, IntegerField
from wtforms.validators import InputRequired, ValidationError, StopValidation, NumberRange
from wtforms_json import init; init()

from openprocurement.auction.esco.constants import DAYS_IN_YEAR, MAX_CONTRACT_DURATION
from openprocurement.auction.esco.utils import calculate_npv 


def validate_bidder_id_on_bidding(form, field):
    stage_id = form.document['current_stage']
    if field.data != form.document['stages'][stage_id]['bidder_id']:
        raise StopValidation(u'Not valid bidder')


def validate_value(form, field):
    data = Fraction(field.data)
    if data <= Fraction('0') and data != -1:
        raise ValidationError(u'To low value')


def _npv(form):
    nbu_rate = form.auction.auction_document['NBUdiscountRate']
    annual_costs_reduction = form.auction.auction_document['value']['annualCostsReduction']
    yearlyPayments = form.yearlyPayments or form.auction.auction_document['value']['yearlyPayments']
    contractDuration = form.contractDuration or form.auction.auction_document['value']['contractDuration']
    if form.yearlyPaymentsPercentage:
        return calculate_npv(nbu_rate, annual_costs_reduction, None,
                             contractDuration,
                             yearlyPaymentsPercentage=form.yearlyPaymentsPercentage,
                             contractDurationDays=form.contractDurationDays)
    else:
        return calculate_npv(nbu_rate, annual_costs_reduction,
                             yearlyPayments, contractDuration,
                             contractDurationDays=form.contractDurationDays)


def validate_bid_change_on_bidding(form, amount_npv):
    """
    Bid must be higher then previous bidder bid amount minus minimalStep amount
    """
    stage_id = form.document['current_stage']
    if form.auction.features:
        max_bid = form.document['stages'][stage_id]['amount_features']
        _max = Fraction(max_bid) * form.auction.bidders_coeficient[form.data['bidder_id']]
        _max += Fraction(form.document['minimalStep']['amount'])
        if amount_npv < _max:
            raise ValidationError(u'Too low value')
    else:
        max_bid = form.document['stages'][stage_id]['amount']
        if amount_npv < (max_bid + form.document['minimalStep']['amount']):
            raise ValidationError(u'Too low value')


class BidsForm(Form):
    bidder_id = StringField(
        'bidder_id',
        [InputRequired(message=u'No bidder id')]
    )

    yearlyPayments = DecimalField(
        'yearlyPayments',
        validators=[validate_value]
    )
    yearlyPaymentsPercentage = DecimalField(
        'yearlyPaymentsPercentage',
        validators=[validate_value]
    )
    contractDuration = IntegerField(
        'contractDuration',
        validators=[NumberRange(1, MAX_CONTRACT_DURATION)]
    )
    contractDurationDays = IntegerField(
        'contractDurationDays',
        validators=[NumberRange(1, DAYS_IN_YEAR)]
    )

    def validate_bidder_id(self, field):
        stage_id = self.document['current_stage']
        if self.document['stages'][stage_id]['type'] == 'bids':
            validate_bidder_id_on_bidding(self, field)

    def validate(self):
        if super(BidsForm, self).validate():
            # TODO:
            if not any([self.yearlyPaymentsPercentage, self.yearlyPayments]):
                raise ValidationError(u'Provide either yearlyPaymentsPercentage or yearlyPayments')
            if self.contractDurationDays and self.contractDuration:
                if (Fraction(contractDurationDays, DAYS_IN_YEAR) + self.contractDuration) > MAX_CONTRACT_DURATION:
                    raise ValidationError(u'Maximun contract duration is 15 years')
            if self.yearlyPayments == -1 or self.yearlyPaymentsPercentage == -1:
                return -1
            amount = _npv(self)
            stage_id = self.document['current_stage']
            if self.document['stages'][stage_id]['type'] == 'bids':
                validate_bid_change_on_bidding(self, amount)
            else:
                raise ValidationError(u'Stage not for bidding')
            return amount 
        return False


def form_handler():
    auction = app.config['auction']
    with auction.bids_actions:
        form = app.bids_form.from_json(request.json)
        form.auction = auction
        form.document = auction.db.get(auction.auction_doc_id)
        current_time = datetime.now(timezone('Europe/Kiev'))
        total_amount = form.validate()
        if total_amount:
            # write data
            auction.add_bid(form.document['current_stage'],{
                'bidder_id': form.data['bidder_id'],
                'amount': total_amount,
                'contractDuration': form.data['contractDuration'],
                'contractDurationDays': form.data['contractDurationDays'],
                'time': current_time.isoformat()
            })
            if form.data['yearlyPayments'] == -1.0 or form.data['yearlyPaymentsPercentage']:
                app.logger.info("Bidder {} with client_id {} canceled bids in stage {} in {}".format(
                    form.data['bidder_id'],
                    session['client_id'],
                    form.document['current_stage'],
                    current_time.isoformat()
                ), extra=prepare_extra_journal_fields(request.headers))
            else:
                app.logger.info("Bidder {} with client_id {} placed bid {} in {}".format(
                    form.data['bidder_id'], session['client_id'],
                    form.data['bid'], current_time.isoformat()
                ), extra=prepare_extra_journal_fields(request.headers))
            return {'status': 'ok', 'data': form.data}
        else:
            app.logger.info("Bidder {} with client_id {} wants place bid {} in {} with errors {}".format(
                request.json.get('bidder_id', 'None'), session['client_id'],
                request.json.get('bid', 'None'), current_time.isoformat(),
                repr(form.errors)
            ), extra=prepare_extra_journal_fields(request.headers))
            return {'status': 'failed', 'errors': form.errors}
