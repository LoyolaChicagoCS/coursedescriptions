'''script to take csv file from Locus class schedule and make
nice .rst files for all courses or those filtered by campus
Assumes <Season><year>.txt file contains texts link or info - maybe more later
Works for Fall, Spring, and Summer
though summer may not be set up in index or T4 
'''

from csv import reader

##example:
##    ['____________________________ ... ', '']
##    ['COMP', ' 150', '002', '3450', 'Introduction to Computing', 'Lecture', '3', '', '']
##    ['', '', '', '', '', '', '(In person)']
##    ['Bldg:', 'Crown Center', 'Room:', '105', 'Days:', 'MW', 'Time:', '04:15PM-05:30', '', 'Instructor:', 'Tuckey,Curtis D']
##    ['Class Enrl Cap:', '25', 'Class Enrl Tot:', '8', 'Class Wait Cap:', '0', 'Class Wait Tot:', '0', 'Class Min Enrl:', '0']
##    ['Class Equivalents:', 'ACCOMP 150/COMP 150']
##    []
##    ['This course is restricted to undergraduate students.']
##    ['Graduate students wishing to enroll in a section of this course should contact their departmental']
##    ['graduate advisor.']
##    ['_________________________________________________ ... ', '']
##    ['', '', '', '', '', '', '', '', '']
##    ['Report ID:  SR201', 'Loyola University Chicago', 'Page No.', '4', 'of', '25']
##    ['Schedule of Classes for Fall 2016', 'Run Date:', '05/13/2016']
##    ['Campus: Lake Shore Campus   Location: Lake Shore Campus', 'Run Time:', '22:28:26']
##    ['', '', '', '', '', '', 'Regular Academic Session']
##    ['College of Arts and Sciences - Computer Science - Subject: Computer Science']
##    []
##    ['____________________________________________________ ... ',
##     'Subject', 'Catalog Nbr', 'Section', 'Class Nbr', 'Course Title', 'Component', 'Units', 'Topics']

# Parts are terminated with separator line starting with many dashes
#   Two types:  page heading and course sections
# All extracted in parseCSV
# Different semester types and campuses are in different pages, 
#    so grabbed from latest page heading:
        # semester type, either regular... or like 7 week - first 
        # enclosing semester like Spring 2019
        # created on csv creation date, time
# Section complications:  multiple date formats, multiple instructors
#    Section data extracted in Section constructor, dict remembered
#         See Section class for more documentation
# In toAllRST for complete or filtered by campus course listing page,
#    extract appropriate course data, make .rst

############## for log of errors/warnings #########

import sys

logList = []
campuses = ['Lake Shore', 'Watertower', 'Online'] 
TESTPREFIX = '' # 'TEST' #DEBUG

def log(s):
    logList.append(s)

def printLog():
    if logList:
        print('\n\nLogged items: ')
        for s in logList:
            print(s)

############# support making .rst ########
def joinIndented(lines, indent):
    'lines is a list of lines.  Return lines indented in one string for .rst'
    if not lines:  return ''
    lines = [indent + line.strip() for line in lines]
    return '\n'.join(lines)


sectionTemplate = '''
:doc:`{docName}`{topic} {term}
    | Section {section} ({regCode}) Credits: {credits}; {mixture}; {format}
    | Instructor: {instructor}
{placeTimes}

{notes}
''' # docName link should give full course title - so not 388/488

comp314_315Template = '''
{area} {number} {term} (Description: :doc:`comp314-315`)
    | Section {section} ({regCode}) Credits: {credits}; {mixture}; {format}
    | Instructor: {instructor}
{placeTimes}

{notes}
'''

topicsSectionTemplate = '''

{area} {number} Topic {topic} {term}
    | Section {section} ({regCode}) Credits: {credits}; {mixture}; {format}
    | Instructor: {instructor}
{placeTimes}
    | Description similar to: :doc:`{docName}`

{notes}
'''      # 388/488  handles links to descritions differently

################## Section class for all section data ##############
class Section:  
    '''Has members (example in paren)
      campus (Online, Lakshore, Watertower, Cuneo)
      term  (regular is '', 8 Week 1)
      instructor (Willaim Honig)
      instructorList(['Honig, William'])
      area (COMP)
      number (170)
      section (002 or 02L)
      regCode (4235)
      title (Introduction to Computing) not used, but check?
      format (Lecture or Laboratory)
      credits (3 or 1-6)
      topic (Foundations of Computer Science I - for 388, 488)
      mixture (In person, Hybrid, Online)
      placeTimes (indented string lines from list of place-days-time-campus)
      notes (indented string of lines)
      crsAbbr (comp150)
      abbr (comp150-001)
      docName (comp150 or special for topics course section))
    '''
    def __init__(self, campus, term, lines, indent = ' '*4): # see .csv example for locations!
        self.campus = campus
        self.term = term
        if lines[2][-1].strip() != 'Instructor:': # may be no field for instructor
            firstInstructor = lines[2][-1]
        else:
            firstInstructor = 'Staff'
        self.instructorList = [firstInstructor]
        self.area = lines[0][0].strip()
        if self.area != 'COMP':
            log('bad line 0:'+lines[0][0])
        self.number = lines[0][1].strip()
        self.section = lines[0][2].strip()
        self.regCode = lines[0][3].strip()
        self.title = lines[0][4].strip()
        self.format = lines[0][5].strip()
        self.credits = lines[0][6].strip()
        self.topic = lines[0][7].strip()
        if self.topic:  self.topic = ': ' + self.topic
        self.mixture = lines[1][-1].strip()[1:-1]
        self.crsAbbr = self.area.lower() + self.number  # just course
        self.abbr = self.crsAbbr + '-' + self.section   # with section
        self.setDocName()
        placeTimeList = [] #allow multiple lines
        i = 2
        lastFriLoc = '' # for courses with makeup Friday - does not find actual dates
        while lines[i] and lines[i][0] == 'Bldg:':
            loc = getPlaceTime(lines[i], campus)
            # assume short term Fridays as later entrues are special, not all term.
            if i>2 and self.term and ', Friday' not in loc and 'Friday' in loc:
                if lastFriLoc != loc:
                    placeTimeList.append(loc + ' - Check week(s)')
                lastFriLoc = loc
            else:
                placeTimeList.append(loc)
            i += 1
            if len(lines[i-1]) == len(lines[i]) and not lines[i][0]: # further instr under orig, empty fields before
                if lines[i][-1] and lines[i][-1] not in self.instructorList:
                     self.instructorList.append(lines[i][-1])
                i += 1

        self.placeTimes = joinIndented(placeTimeList, indent + '| ')  # force separate lines
        self.instructorList.sort()
        self.instructor = ', '.join([parse_instructor(instr) for instr in self.instructorList])
        if lines[i] and lines[i][0] == 'Class Enrl Cap:': #look for more unused line types in future
            i += 1
        if lines[i] and (lines[i][0] == 'Class Equivalents:' or lines[i][0] == 'Attributes:'):
            i += 1
        if lines[i] and (lines[i][0] == 'Room Characteristics:' or lines[i][0] == 'Class Equivalents:'):
            i += 1
        if lines[i] and lines[i][0]: # in case another line, not all empties
            i += 1
        # ',,,,,,' line before notes,and notes are at the end:  process the rest
        notes = [line[0] if line else '' for line in lines[i:-1] ] # skip dashes line at end

        if notes:
            notes[0] = '**Notes:** ' + notes[0].strip()
        self.notes = joinIndented(notes, indent).rstrip()

    def setDocName(self): # this is the course with documentation - may be different for 388/488
        #assume 388/488 convention for section > 100, section is corresponding linked course
        specialSect = { '502': '305'
                      }                               ## todo: make not hardcoded, need now?
        self.docName = self.crsAbbr
        if self.crsAbbr in ['comp388', 'comp488']:
            if specialSect.get(self.section):
                self.docName = 'comp' + specialSect[self.section]
            elif '500' > self.section >= '100':
                self.docName = 'comp' + self.section
            else:
                self.docName = 'No comparison'  # KLUDGE for toSectRST (next function)!


    def toSectRST(self):  # this section to .rst lines
        if self.crsAbbr in ['comp314', 'comp315']:
            return comp314_315Template.format(**self.__dict__)
        if self.crsAbbr == self.docName: # not 388/488
            return sectionTemplate.format(**self.__dict__)
        s = topicsSectionTemplate.format(**self.__dict__)
        if 'No comparison' in s:    # KLUDGE!
            s = s.replace('''    | Description similar to: :doc:`No comparison`''', '')
        return s

    def __lt__(self, other): # so list in course  and section order
        return self.abbr < other.abbr

############ support Section field formating ###########

def getPlaceTime(line, campus):
    'Return string for place, time, campus; online, TBA treated specially'
    bldg = line[1].strip()
    room = line[3].strip()
    days = parse_days(line[5])
    clock = line[7].strip()
    if clock == 'TBA':
        time = 'Times: TBA'
    else:
        time = days + ' ' + clock
    if campus == 'Online':
        return 'Online ' + time
    if room == 'TBA':
        place = 'Place TBA'
    else:
        place = bldg+ ':' + room
    return '{} ({}) {}'.format(place, campus, time)

def parse_days(days):
    'Remove day abbreviations: MWF -> Monday, Wednesday, Friday'
    days = days.strip()
    if days in ['See Note', 'TBA']:
       return days
    orig = days
    full = []
    for (abbr, day) in [('M', 'Monday'), ('Tu', 'Tuesday'), ('W', 'Wednesday'),
                            ('Th', 'Thursday'), ('F', 'Friday'), ('Sa', 'Saturday')]:
        if abbr in days:
            full.append(day)
            days = days.replace(abbr, '')
    if days or not orig:
        log('Bad days code ' + orig)
        return 'TBA'
    return ', '.join(full)

# decodes the instructor names putting them in order: "Smith,Adam" = Adam Smith
def parse_instructor(instructor):
    parts = instructor.split(',')
    if '' in parts:   # not sure why this
        return 'TBA'
    else:
        parts.reverse()
        return ' '.join(parts)

############## for 391/490 special - single nentry with list of instructors

indepStudyTemplate = '''
:doc:`{}` 1-6 credits
    You cannot register
    yourself for an independent study course!
    You must find a faculty member who
    agrees to supervisor the work that you outline and schedule together.  This
    *supervisor arranges to get you registered*.  Possible supervisors are: {}
'''

def getFacNames(crsAbbr, courses):  # all faculty of indep study sections together
    names = []
    for section in courses:
        if courses[section].crsAbbr == crsAbbr:
           names += courses[section].instructorList
    names = [name for name in names if name != 'Staff']
    names.sort()  # name last-first for sorting
    names = [parse_instructor(name) for name in names]
    if names:
        return ', '.join(names)
    return  'full-time department faculty'   #KLUDGE until names added

############## collapse lab sections into main #######

def fixLabs(courses): # shorten by listing labs with main course section, deleting lab entry
    for name, sect in list(courses.items()):
        if sect.section.endswith('L'):
            mainAbbr = name.replace('-', '-0')[:-1] # comp170-02L -> comp170-002
            mainSect = courses.get(mainAbbr)
            if mainSect:
                mainSect.format += '/Lab'
                mainSect.placeTimes += '\n' + sect.placeTimes + ' (lab)'
                mainSect.section += '/' + sect.section
                del(courses[name])

########### more support for .rst file ########

def doLevelRST(names, indep, rstParts, courses):
    'Assemble grad or undergrad part with special independent study entry'
    names.sort()
    for sect in names:
        if sect == indep:
            facNames = getFacNames(indep, courses)
            rstParts.append(indepStudyTemplate.format(sect, facNames))
        else:
            course = courses.get(sect)
            if course:  # so not deleted lab section  # now deleted earlier - need?
                rstParts.append(course.toSectRST())

def campSeasonToDocName(camp, season): # campus and season make the document name 
    camp = camp.replace(' ', '');
    return TESTPREFIX + (camp + season).lower()


def toAllRST(courses, semester, created, mainCampus, textURL=''):
    '''return the entire rst file contents
    courses:  courses[abbr] = section
    semester:  like Fall 2019
    created:  Updated csv date and time
    mainCampus:  '' means all, or Lake Shore, Watertower, Online
    textURL URL or note to show about later text link
    '''

    headingTemplate = '''
{semester} Schedule {specialFilter}
==========================================================================
{created}

The following courses will (tentatively) be held during the {semester} semester.

For open/full status and latest changes, see
`LOCUS <http://www.luc.edu/locus>`_.

**In case of conflict, information on LOCUS should be considered authoritative.**

{txtBookURLline}

Section titles lines link to the course description page,
except for special topics courses.  
Some of those later show a link to a related course description.

The 4-digit number in parentheses after the section is the Locus registration code.

Be sure to look at the section's notes or Locus for an 8-week courses with more than one schedule line:
Friday line(s) are likely to be isolated makeup days, not every week.

You can skip over undergrad courses to :ref:`{gradTarget}`.

**View Campus Specific Courses below :**

{campusURLTemplate}



.. _{undergradTarget}:

Undergraduate Courses
~~~~~~~~~~~~~~~~~~~~~~~~~~~

'''  # verbiage for top of each schedule

    gradHeadingTemplate = '''

.. _{gradTarget}:

Graduate Courses
~~~~~~~~~~~~~~~~~~~~~

''' # target  and headinf ofr html target

    # heading insertions
    season = semester.split()[0].lower()
    txtBookURLTemplate= 'See `Textbook Information <{textURL}>`_.'
    txtBookURLline = ('See `Textbook Information <{}>`_.'.format(textURL) if '://' in textURL
                      else textURL)
    thisDoc = campSeasonToDocName(mainCampus, season)
    undergradTarget = thisDoc + '_undergraduate_courses_list'
    gradTarget = thisDoc + '_graduate_courses_list'

    if mainCampus == 'Online':
        specialFilter = '( Online )'
    elif mainCampus:
        specialFilter = '( {} Campus )'.format(mainCampus)
    else:
        specialFilter = ''

    campusURLTemplate= '' # set up other campuses for links
    for camp in [''] + campuses:
        if camp !=  mainCampus:
            campusURLTemplate += '\n* :doc:`{}`'.format(campSeasonToDocName(camp, season))

    parts = [headingTemplate.format(**locals())] # make heading

    abbrFilt = [abbr for (abbr, section) in courses.items() # filter sections
                    if mainCampus in section.campus]
    # add undergrad part                
    undergrad = ['comp398'] + [abbr for abbr in abbrFilt   # one placeholder for 398
                               if courses[abbr].area == 'COMP' and
                                  '398' != courses[abbr].number < '400']
    doLevelRST(undergrad, 'comp398', parts, courses)

    # add grad part
    parts.append(gradHeadingTemplate.format(**locals()))
    grad = ['comp490'] + [abbr for abbr in abbrFilt  # one placeholder for 490
                          if courses[abbr].area == 'COMP' and
                             '490' != courses[abbr].number >= '400']
    doLevelRST(grad, 'comp490', parts, courses)

    return '\n'.join(parts)

############# for parsing ####################

def getLines(rawLines):
    '''return csv list of entries for each line,
    If rawLines is a string it is taken as a csv file name'''
    if isinstance(rawLines, str):
        with open(rawLines) as inf:
            lines = list(reader(inf))
        #printLines(lines, 15)
        return lines
    return list(reader(rawLines))


def isDashes(s): # recognize csv part separator
    return s.startswith('_____________')

def getToDashes(lines): # section lines through EOF or ending dashes
    part = []
    while lines:
        line = lines.pop() # line is list from the comma separated list
        part.append(line)
        if line and isDashes(line[0]):
            return part               # so dashes line at end of what returned
    return None


def parseCSV(csvFile):
    '''return dictionary of courses, semester heading data'''
    lines = getLines(csvFile)
    lines.reverse()
    #printLines(lines, -15) #DEBUG
    courses = {}
    campus = 'Not set'  # like Lake Shore
    term = 'Not set'  # empty for default main session, or like Seven Week - First
    semester = 'Not set' # like Spring 2019
    created = 'Not set'  # csv creation: Updated: date and time

    while(lines):  # one part through dashes at a time
        part = getToDashes(lines)
        if part is None:
            #print('At end!') #DEBUG
            return (courses, semester, created)
        #print('Current section: ') #DEBUG
        #for line in part: #DEBUG
        #    print(line)
        if part[-1][-1] == 'Topics': # page header
            if not part[0][0]:  #empty commas at start for all but first page
                part = part[1:]
            #print('Parsing page', part[0][3], 'semester', part[1][0]) #DEBUG
            semester = ' '.join(part[1][0].split()[-2:]) # last two words of first entry in second line
            date = part[1][2]
            time = part[2][2]
            campus = part[2][0].partition('Location')[0].strip().replace('Campus: ', '').replace(' Campus', '')
            # print(campus)  #DEBUG
            # assume campus and location same?
            term = part[3][0] # empty string for regular session

            if term == 'Regular Academic Session': # less verbose omitting standard session
            	term = ''
            if term:
                term = '[Term: ' + term + ']'
            created = 'Updated {} {}'.format(date, time)
            #not in use
            #if not term and part[3][6] != 'Regular Academic Session':
              # term = '[Term: ' + part[3][6] + ']'
        else:  # part is section description
            #print('Processing section') #DEBUG
            section = Section(campus, term, part)
            courses[section.abbr] = section
        #input('press return: ')  #DEBUG


def main(csvFileName=None):
    if not csvFileName:
        csvFileName=input("Enter CSV file name base (like fall2018): ")
    if not csvFileName.endswith('.csv'):
        csvFileName += '.csv'
    print("Make sure last year's semester is archived!")
    (courses, semester, created) = parseCSV(csvFileName)
    fixLabs(courses)
    season = semester.split()[0].lower() # like Spring 2019 -> spring
    with open(semester.replace(' ', '') + '.txt') as inf: # Spring 2019 -> Spring2019.txt
        semesterData = inf.readlines()
    textURL = semesterData[0].strip() # comment on omission of texts, or URL
    # more data later?

    for mainCampus in [''] + campuses:
        rst = toAllRST(courses, semester, created, mainCampus, textURL)
        fName = campSeasonToDocName(mainCampus, season) + '.rst'
        fName = 'source/' + fName
        with open(fName, 'w') as outf:
            outf.write(rst)
        print('Wrote ' + fName)
    printLog()

############ just debugging ####################
def printLines(lines, n):  # for debugging
    'front n > 0; end, backwards, n <0'
    if n >0:
        n = min(n, len(lines))
        print('\nprinting', n, 'lines:')
        for line in lines[:n]:
            print(line)
    else:
        n = min(-n, len(lines))
        print('\nprinting', n, 'lines from end back:')
        for line in lines[-1:-n-1:-1]:
            print(line)

f = None
if sys.argv[1:]:
    f = sys.argv[1]
main(f)
