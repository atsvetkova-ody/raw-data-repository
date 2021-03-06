from code_constants import UNSET, RACE_AIAN_CODE, RACE_ASIAN_CODE, RACE_BLACK_CODE, RACE_MENA_CODE
from code_constants import RACE_NHDPI_CODE, RACE_WHITE_CODE, RACE_HISPANIC_CODE, RACE_FREETEXT_CODE
from code_constants import PMI_SKIP_CODE, PMI_PREFER_NOT_TO_ANSWER_CODE, PMI_OTHER_CODE
from code_constants import PMI_FREE_TEXT_CODE, PMI_UNANSWERED_CODE
import extraction
from protorpc import messages
from dateutil.relativedelta import relativedelta

# These are handled specially in code; others will be inserted into the database and handled
# dynamically.
UNSET_HPO_ID = 0

# A pattern for test participant email addresses.
TEST_EMAIL_PATTERN = '%@example.com'
# The name of the 'test' HPO that test participants are normally affiliated with.
TEST_HPO_NAME = 'TEST'

class PhysicalMeasurementsStatus(messages.Enum):
  """The state of the participant's physical measurements"""
  UNSET = 0
  COMPLETED = 1

class QuestionnaireStatus(messages.Enum):
  """The status of a given questionnaire for this participant"""
  UNSET = 0
  SUBMITTED = 1
  SUBMITTED_NO_CONSENT = 2

class EnrollmentStatus(messages.Enum):
  """A status reflecting how fully enrolled a participant is"""
  INTERESTED = 1
  MEMBER = 2
  FULL_PARTICIPANT = 3

class SampleStatus(messages.Enum):
  """Status of biobank samples"""
  UNSET = 0
  RECEIVED = 1

# These race values are derived from one or more answers to the race/ethnicity question
# in questionnaire responses.
class Race(messages.Enum):
  UNSET = 0
  SKIPPED = 1
  UNMAPPED = 2
  AMERICAN_INDIAN_OR_ALASKA_NATIVE = 3
  BLACK_OR_AFRICAN_AMERICAN = 4
  ASIAN = 5
  NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER = 6
  WHITE = 7
  HISPANIC_LATINO_OR_SPANISH = 8
  MIDDLE_EASTERN_OR_NORTH_AFRICAN = 9
  HLS_AND_WHITE = 10
  HLS_AND_BLACK = 11
  HLS_AND_ONE_OTHER_RACE = 12
  HLS_AND_MORE_THAN_ONE_OTHER_RACE = 13
  MORE_THAN_ONE_RACE = 14
  OTHER_RACE = 15
  PREFER_NOT_TO_SAY = 16

# A type of organization responsible for signing up participants.
class OrganizationType(messages.Enum):
  UNSET = 0
  # Healthcare Provider Organization
  HPO = 1
  # Federally Qualified Health Center
  FQHC = 2
  # Direct Volunteer Recruitment Center
  DV = 3
  # Veterans Administration
  VA = 4

ANSWER_CODE_TO_RACE = {
  RACE_AIAN_CODE: Race.AMERICAN_INDIAN_OR_ALASKA_NATIVE,
  RACE_ASIAN_CODE: Race.ASIAN,
  RACE_BLACK_CODE: Race.BLACK_OR_AFRICAN_AMERICAN,
  RACE_MENA_CODE: Race.MIDDLE_EASTERN_OR_NORTH_AFRICAN,
  RACE_NHDPI_CODE: Race.NATIVE_HAWAIIAN_OR_OTHER_PACIFIC_ISLANDER,
  RACE_WHITE_CODE: Race.WHITE,
  RACE_HISPANIC_CODE: Race.HISPANIC_LATINO_OR_SPANISH,
  RACE_FREETEXT_CODE: Race.OTHER_RACE,
  PMI_SKIP_CODE: Race.SKIPPED,
  PMI_PREFER_NOT_TO_ANSWER_CODE: Race.PREFER_NOT_TO_SAY,
  PMI_OTHER_CODE: Race.OTHER_RACE,
  PMI_FREE_TEXT_CODE: Race.OTHER_RACE,
  PMI_UNANSWERED_CODE: Race.UNSET
}


class WithdrawalStatus(messages.Enum):
  """Whether a participant has withdrawn from the study."""
  NOT_WITHDRAWN = 1
  NO_USE = 2


class SuspensionStatus(messages.Enum):
  """Whether a participant has been suspended from the study."""
  NOT_SUSPENDED = 1
  NO_CONTACT = 2


# The lower bounds of the age buckets.
_AGE_LB = [0, 18, 26, 36, 46, 56, 66, 76, 86]
AGE_BUCKETS = ['{}-{}'.format(b, e) for b, e in zip(_AGE_LB, [a - 1 for a in _AGE_LB[1:]] + [''])]

def extract_bucketed_age(participant_hist_obj):
  if participant_hist_obj.date_of_birth:
    bucketed_age = get_bucketed_age(participant_hist_obj.date_of_birth, participant_hist_obj.date)
    if bucketed_age:
      return extraction.ExtractionResult(bucketed_age, True)
  return extraction.ExtractionResult(None, False)

def get_bucketed_age(date_of_birth, today):
  if not date_of_birth:
    return UNSET
  age = relativedelta(today, date_of_birth).years
  for begin, end in zip(_AGE_LB, [age_lb - 1 for age_lb in _AGE_LB[1:]] + ['']):
    if (age >= begin) and (not end or age <= end):
      return str(begin) + '-' + str(end)

def _map_single_race(code):
  if code is None:
    return Race.UNMAPPED
  race_value = ANSWER_CODE_TO_RACE.get(code.value)
  if race_value:
    return race_value
  return ANSWER_CODE_TO_RACE.get(code.parent)

def get_race(race_codes):
  '''Transforms one or more race codes from questionnaire response answers about race
  into a single race enum; the enum includes values for multiple races.
  See: https://docs.google.com/document/d/1Z1rGULWVlmSIAO38ACjMnz0aMuua3sKqFZXjGqw3gqQ'''
  if not race_codes:
    return None
  if len(race_codes) == 1:
    return _map_single_race(race_codes[0])
  else:
    all_races = set([_map_single_race(race_code) for race_code in race_codes])
    if Race.HISPANIC_LATINO_OR_SPANISH in all_races:
      if len(all_races) > 2:
        return Race.HLS_AND_MORE_THAN_ONE_OTHER_RACE
      if Race.WHITE in all_races:
        return Race.HLS_AND_WHITE
      if Race.BLACK_OR_AFRICAN_AMERICAN in all_races:
        return Race.HLS_AND_BLACK
      return Race.HLS_AND_ONE_OTHER_RACE
    else:
      return Race.MORE_THAN_ONE_RACE
