
class Calendar(): # controls the time in game. to advance time in game we do it with this.
    def __init__(self, SECONDS, MINUTES, HOURS, DAYS, MONTHS, YEARS):
        self.SECONDS = SECONDS
        self.MINUTES = MINUTES
        self.HOURS = HOURS
        self.DAYS = DAYS
        self.MONTHS = MONTHS
        self.YEARS = YEARS
        self.SEASON = 'Spring' # 'Summer', 'Winter', 'Fall'
        self.SECONDS_PER_MINUTE = 60
        self.MINUTES_PER_HOUR = 60
        self.HOURS_PER_DAY = 24
        self.DAYS_PER_MONTH = 28
        self.MONTHS_PER_YEAR = 12
        self.TURN = self.SECONDS + int(self.MINUTES * self.SECONDS_PER_MINUTE) + int(self.HOURS * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR) + int(self.DAYS * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY) + int(self.MONTHS  * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY * self.DAYS_PER_MONTH) + int(self.YEARS   * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR)

    def do_events(self): # if we need to do something every so often we should set it up here.
        return

    def advance_time_by_x_seconds(self, amount):
        for x in range(amount):
            self.SECONDS = self.SECONDS + 1
            self.do_events() # if anything needs doing this will do it.
            if(self.SECONDS >= self.SECONDS_PER_MINUTE):
                self.SECONDS = 0
                self.MINUTES = self.MINUTES + 1

            if(self.MINUTES >= self.MINUTES_PER_HOUR):
                self.MINUTES = 0
                self.HOURS = self.HOURS + 1

            if(self.HOURS >= self.HOURS_PER_DAY):
                self.HOURS = 0
                self.DAYS = self.DAYS + 1

            if(self.DAYS >= self.DAYS_PER_MONTH):
                self.DAYS = 0
                self.MONTHS = self.MONTHS + 1

            if(self.MONTHS >= self.MONTHS_PER_YEAR):
                self.MONTHS = 0
                self.YEARS = self.YEARS + 1

    def get_turn(self):
        self.TURN = self.SECONDS + int(self.MINUTES * self.SECONDS_PER_MINUTE) + int(self.HOURS * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR) + int(self.DAYS * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY) + int(self.MONTHS  * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY * self.DAYS_PER_MONTH) + int(self.YEARS   * self.SECONDS_PER_MINUTE * self.MINUTES_PER_HOUR * self.HOURS_PER_DAY * self.DAYS_PER_MONTH * self.MONTHS_PER_YEAR)

        return self.TURN

    def moon_phase(self): # moon phases are 1/4 month roughly
        # 28 days / 4 phases.
        # First Quarter, Full Moon, Third Quarter, New Moon
        if self.DAYS < self.DAYS_PER_MONTH * 0.25:
            return 'First Quarter'
        elif self.DAYS < self.DAYS_PER_MONTH * 0.5:
            return 'Full Moon'
        elif self.DAYS < self.DAYS_PER_MONTH * 0.75:
            return 'Third Quarter'
        else:
            return 'New Moon'

    def get_season(self):
        self.season_names = []
        self.season_names.insert(len(self.weekday_names), 'Spring') # 0
        self.season_names.insert(len(self.weekday_names), 'Summer') # 1
        self.season_names.insert(len(self.weekday_names), 'Winter') # 2, etc..
        self.season_names.insert(len(self.weekday_names), 'Fall')
        if self.MONTHS < self.MONTHS_PER_YEAR * 0.25:
            self.SEASON = 'Spring'
        elif self.MONTHS < self.MONTHS_PER_YEAR * 0.5:
            self.SEASON = 'Summer'
        elif self.MONTHS < self.MONTHS_PER_YEAR * 0.75:
            self.SEASON = 'Winter'
        else:
            self.SEASON = 'Fall'

        return self.SEASON

    def sunrise(self):
        return

    def sunset(self):
        return

    def current_daylight_level(self):
        return

    def sunlight(self):
        return

    def day_of_week(self):
        self.weekday_names = []
        self.weekday_names.insert(len(self.weekday_names), 'Sunday') # 0
        self.weekday_names.insert(len(self.weekday_names), 'Monday') # 1
        self.weekday_names.insert(len(self.weekday_names), 'Tuesday') # 2, etc..
        self.weekday_names.insert(len(self.weekday_names), 'Wednesday')
        self.weekday_names.insert(len(self.weekday_names), 'Thursday')
        self.weekday_names.insert(len(self.weekday_names), 'Friday')
        self.weekday_names.insert(len(self.weekday_names), 'Saturday')
        days = self.DAYS # 0 to DAYS_PER_MONTH
        while(days >= 7): # loop until we get a number 0-6
            days = days - 7

        return self.weekday_names[days] # what's left over is the day of the week.