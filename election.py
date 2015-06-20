# -*- coding: utf-8  -*-

#import pwb #only needed if you haven't installed the framework as side-package
import pywikibot
import sys
import os
import re
import json
import getopt
 
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(PROJECT_DIR, 'pywikibot'))

import pywikibot.compat.catlib as catlib
import pywikibot.page as page
import dateutil.parser as parser 

class HarvestRobot:
    """
    A bot to add Wikidata claims
    """
    def __init__(self, site, templateTitle, fields, valuesConstraints):
        """
        Arguments:
            * generator     - A generator that yields Page objects.
            * templateTitle - The template to work on
            * fields        - A dictionary of fields that are of use to us

        """
        self.templateTitle = templateTitle.replace(u'_', u' ')
        self.fields = fields
        self.valuesConstraints = valuesConstraints
        self.site = site
        self.repo = self.site.data_repository()
        self.setSource(site.language())
        

    def setSource(self, lang):
      '''
      Get the source
      '''
      page = pywikibot.Page(self.repo, 'Wikidata:List of wikis/python')
      source_values = json.loads(page.get())
      source_values = source_values['wikipedia']
      for langue in source_values:
	source_values[langue] = pywikibot.ItemPage(self.repo, source_values[langue])
      
      if lang in source_values:
	  self.source = pywikibot.Claim(self.repo, 'p143')
	  self.source.setTarget(source_values.get(lang))
        
        
    def procesPage(self, site, page):
        """
        Proces a single page
        """
        pywikibot.output('Processing %s' % page)
        try:
	  item = pywikibot.ItemPage.fromPage(page)
	except pywikibot.exceptions.NoPage:
	    pywikibot.output(u'No wikidata for: %s ' % page)
	    return
	
        if not item.exists():
            pywikibot.output('%s doesn\'t have a wikidata item :' % page)
            #TODO FIXME: We should provide an option to create the page
        else:
            pagetext = page.get()
            pagetext = pywikibot.removeDisabledParts(pagetext)
            templates = pywikibot.extract_templates_and_params(pagetext)
            #pywikibot.output( u'Templates: %s' % templates)
            for (template, fielddict) in templates:
                # We found the template we were looking for
                linkedTemplate = pywikibot.Page(self.site, template, ns=10)
                try:
		  if linkedTemplate.isRedirectPage():
                   template2 = linkedTemplate.getRedirectTarget().title()
                   pywikibot.output(
                                    u'Template redirection from %s to %s'
                                    % (template, template2))
                   template = template2[9:]
                except pywikibot.exceptions.InvalidTitle:
		  pywikibot.output("[[%s]]  contains illegal char(s)"
                                            % template)
               
                if template.replace(u'_', u' ') == self.templateTitle:
                     #pywikibot.output( u'Template: %s' % template)
                     for field, value in fielddict.items():
                        # This field contains something useful for us
                        field = field.strip()
                        #pywikibot.output('    field <%s>' % field )
                        # pywikibot.output('    self.fields %s' % (field in self.fields))
                        if (value != "") and (field in self.fields):
                            # Check if the property isn't already set
                            #pywikibot.output('    attribut %s' % field)
                            claim = self.fields[field]
                            if claim[2:-2] in item.get().get('claims'):
                                pywikibot.output(
                                    u'A claim for %s already exists. Skipping'
                                    % (claim,))
                                # TODO FIXME: This is a very crude way of dupe
                                # checking
                            else:
                                # Try to extract a valid page
                                match = re.search(re.compile(
                                    r'\[\[(?P<title>[^\]|[#<>{}]*)(\|.*?)?\]\]'),
                                                  value)
                                #pywikibot.output(u'      cherche %s ' % value)
                                if True:
                                    try:
                                        value = value.strip()
                                        #Date treatement
                                        if claim == "[[P585]]" and value != "":
                                            try:
                                                pywikibot.output(u'      Date: <%s> ' % value)
                                                laDate = parser.parse(value)
                                                pywikibot.output(u'      Date: <%s> ' % laDate)
                                                repo = site.data_repository() # utile self.repo existe ?
                                                theClaim = pywikibot.Claim(repo, claim[2:-2])
                                                # pywikibot.output(u'      Year: %s, Month: %s, Day: %s ' % laDateText[0:3], laDateText[5:6], laDateText[7:8])
						pywikibot.output('Adding %s --> %s'
								% (claim,
								    laDate))
                                                laDate = pywikibot.WbTime(year=laDate.year, month=laDate.month, day=laDate.day)
                                                theClaim.setTarget(laDate)
                                                item.addClaim(theClaim)  
                                                if self.source:
						  theClaim.addSource(self.source, bot=True)
                                            except ValueError:
                                                pywikibot.output(u'      Impossible to parse this date : %s ' % value)
                                                continue
					    continue
					  
                                        if value[:2] == "[[" and value[-2:] == "]]":
					     link = value[2:-2]
                                        else:
                                            link = value
                                        #pywikibot.output(u'      link: <%s> ' % link)
                                        if link == "":
					  continue
                                        #link = match.group(1)
                                        linkedPage = pywikibot.Page(self.site, link)
                                        if linkedPage.isRedirectPage():
                                            linkedPage = linkedPage.getRedirectTarget()
                                        #pywikibot.output(u'      linkedPage %s ' % linkedPage)
                                        linkedItem = pywikibot.ItemPage.fromPage(linkedPage)
                                        linkedItem.get()
                                        if not linkedItem.exists():
					   pywikibot.output('%s doesn\'t have a wikidata item :' % linkedPage)
					   continue
                                        
                                        #value constraints treatement
                                        if (claim in self.valuesConstraints) and (linkedItem.getID() not in  self.valuesConstraints[claim]):
                                             pywikibot.output(u'The value of the property %s is %s does not respect the constraint %s' % 
                                                                       (claim,
                                                                       linkedItem.title(),
                                                                       self.valuesConstraints[claim]))
                                             continue
                                        
                                        #instance of constraint treatment
                                        if claim == "[[P541]]":
					  linkedItem.get()  # you need to call it to access any data.
					  if linkedItem.claims and ('P31' in linkedItem.claims):
					    if linkedItem.claims['P31'][0].getTarget().title(withNamespace=False) != "Q4164871":
						pywikibot.output(u'The P31 value is not Q4164871 but %s ' % linkedItem.claims['P31'][0].getTarget().title(withNamespace=True))
						continue
					  else:
					    pywikibot.output(u'The P31 value is missing ')
					    continue
                                        
                                        #pywikibot.output(u'      linkedItem %s ' % linkedItem)
                                        #pywikibot.output(u'      linkedItem.getID() %s ' % linkedItem.title()[1:])
                                        pywikibot.output('Adding %s --> %s'
                                                         % (claim,
                                                            linkedItem.getID()))
                                        repo = site.data_repository() # utile self.repo existe ?
                    
                                        theClaim = pywikibot.Claim(repo, claim[2:-2])
                                        theClaim.setTarget(linkedItem)
                                        item.addClaim(theClaim)
                                        if self.source:
                                           theClaim.addSource(self.source, bot=True)
                                    except pywikibot.NoPage:
                                        pywikibot.output(
                                            "[[%s]] doesn't exist so I can't link to it"
                                            % linkedPage)
                                    except pywikibot.exceptions.InvalidTitle:
                                        pywikibot.output(
                                            "[[%s]] is an invalid title"
                                            % link)


def processCategory(wikipediaSource, template, categoryname, fields, valuesConstraints):
         site = pywikibot.Site(wikipediaSource,'wikipedia') #  any site will work, this is just an example
         hr = HarvestRobot(site, template, fields, valuesConstraints)
         category = catlib.Category(site, "%s:%s" % (site.namespace(14), categoryname))
         for page in category.articles(recurse=True, startFrom=None): 
              hr.procesPage(site, page)
                                            
def processOnePage(wikipediaSource, template, laPage, fields, valuesConstraints):
         site = pywikibot.Site(wikipediaSource,'wikipedia') #  any site will work, this is just an example
         hr = HarvestRobot(site, template, fields, valuesConstraints)
         p =pywikibot.Page(site, laPage)
         hr.procesPage(site, p)
                                            
                                            
templateName =  dict()
templateName["en"] = u"Infobox election"
templateName["es"] = u"Ficha de elección"

fields = dict()
valuesConstraints = dict()
fields["country"] = "[[P17]]"
fields[u"país"] = "[[P17]]"
valuesConstraints["[[P17]]"] = set(["Q889", "Q222", "Q262", "Q228", "Q916", "Q781", "Q414", "Q399", "Q408", "Q40", "Q227", "Q778", "Q398", "Q902", "Q244", "Q184", "Q31", "Q242", "Q962", "Q917", "Q750", "Q225", "Q963", "Q155", "Q921", "Q219", "Q965", "Q967", "Q424", "Q1009", "Q16", "Q1011", "Q929", "Q657", "Q298", "Q148", "Q739", "Q970", "Q800", "Q1008", "Q224", "Q241", "Q229", "Q213", "Q33946", "Q974", "Q756617", "Q977", "Q784", "Q786", "Q574", "Q736", "Q79", "Q792", "Q983", "Q986", "Q191", "Q115", "Q702", "Q712", "Q33", "Q142", "Q1000", "Q1005", "Q230", "Q183", "Q117", "Q41", "Q769", "Q774", "Q1006", "Q1007", "Q734", "Q790", "Q783", "Q28", "Q189", "Q668", "Q252", "Q794", "Q796", "Q27", "Q801", "Q38", "Q766", "Q17", "Q810", "Q232", "Q114", "Q710", "Q817", "Q813", "Q819", "Q211", "Q822", "Q1013", "Q1014", "Q1016", "Q347", "Q37", "Q32", "Q221", "Q1019", "Q1020", "Q833", "Q826", "Q912", "Q233", "Q709", "Q1025", "Q1027", "Q96", "Q217", "Q711", "Q236", "Q235", "Q1028", "Q1029", "Q836", "Q1030", "Q697", "Q837", 
                                    "Q29999", "Q664", "Q811", "Q1032", "Q1033", "Q423", "Q20", "Q842", "Q843", "Q695", "Q804", "Q691", "Q733", "Q419", "Q928", "Q36", "Q45", "Q846", "Q971", "Q218", "Q159", "Q1037", "Q763", "Q760", "Q757", "Q683", "Q238", "Q1039", "Q851", "Q1041", "Q403", "Q1042", "Q1044", "Q334", "Q214", "Q215", "Q685", "Q1045", "Q258", "Q884", "Q958", "Q29", "Q854", "Q1049", "Q730", "Q1050", "Q34", "Q39", "Q858", "Q863", "Q924", "Q869", "Q945", "Q678", "Q754", "Q948", "Q43", "Q874", "Q672", "Q1036", "Q212", "Q878", "Q145", "Q30", "Q77", "Q265", "Q686", "Q237", "Q717", "Q881", "Q180573", "Q805", "Q36704", "Q953", "Q954", "Q28513", "Q2895", "Q618399", "Q179876", "Q5291089", "Q70972", "Q7735661", "Q41304""7318", "Q713750", "Q16957", "Q5555325", "Q161885", "Q5622720", "Q156418", "Q223936", "Q172579", "Q6392538", "Q6741448", "Q7603765", "Q14759030", "Q12560", "Q2006542", "Q211274", "Q27306", "Q34266", "Q2184", "Q230791", "Q14920623", "Q193619", "Q15180", "Q170588", "Q7842409", "Q7877575", 
                                    "Q174193", "Q191077", "Q723118", "Q43287", "Q12548", "Q1747689", "Q844930", "Q2429397", "Q23334", "Q865", "Q1246", "Q407199", "Q6250", "Q55", "Q21203", "Q25279", "Q26273", "Q35", "Q223", "Q4628", "Q34020", "Q33788"])

#fields["previous_election"] = "[[P155]]"
#fields["next_election"] = "[[P156]]"
#fields["type"] = "[[P31]]"
#valuesConstraints["[[P31]]"] = set(["Q858439", "Q1076105", "Q152450", "Q669262", "Q1128324"])
fields["after_election"] = "[[P991]]"
fields["sucesor"] = "[[P991]]"
fields["election_date"] = "[[P585]]" 
fields[u"fecha_elección"] = "[[P585]]" 
fields["title"] = "[[P541]]"
fields["cargo"] = "[[P541]]"

try:
  opts, args = getopt.getopt(sys.argv[1:], "p", ["page"])
except getopt.GetoptError as err:
  print("erreur", err)
  sys.exit(2)

mode = "categoryMode"
#print(opts)
for o, a in opts:
  if o == "-p":
    mode = "pageMode"
  else:
    mode = "categoryMode"
    
if mode == "pageMode":
  processOnePage(args[1], templateName[args[1]], args[0].decode("utf8"), fields, valuesConstraints)
else:
  #processCategory( u"en", u"Infobox election", u"Presidential elections in Romania", fields, valuesConstraints)
  processCategory( args[1], templateName[args[1]], args[0].decode("utf8"), fields, valuesConstraints)

