
#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2014
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/"""Partial Least Squares Regression Module"""

__author__ =  'JB, JKP, spss'
__version__=  '1.1.4'

#Licensed Materials - Property of IBM
#IBM SPSS Products: Statistics General
#(c) Copyright IBM Corp. 2007, 2011
#US Government Users Restricted Rights - Use, duplication or disclosure restricted by GSA ADP Schedule Contract with IBM Corp.

# history
# 07-apr-2010 workaround pivot table bug when single column
# 02-mar-2011 try even harder to find the scipy cg function
# 04-mar-2011 Expose warning messages from UNIANOVA block
# 05-dec-2011 Enable translation
# 12-jun-2013 tweak translation setup
# 12-dec-2013 deal with very long variable lists in UNIANOVA
# 19-nov-2014 handle case of no covariates

import spss, re
from random import uniform
import textwrap

try:
    import spssaux, spssdata, extension
except:
    # nontranslatable messages...
    print """This module requires the spssaux, spssdata, namedtuple and extension modules from
              SPSS Developer Central, www.spss.com/devcentral.  One or more was not found.
              Please download these and try again"""
    raise ImportError
if int(spssaux.__version__[0]) < 2 or int(spssdata.__version__[0]) < 2:
    print """This module requires at least version 2.0.0 of spssaux and spssdata.  Please download a newer version from SPSS Developer Central"""
    raise ImportError
#if int(extension.__version__[0]) < 1 or (int(extension.__version__[0]) == 1 and int(extension.__version__[2]) < 1):
#	print """This module requires at least version 1.1.0 of spssaux and spssdata.  Please download a newer version from SPSS Developer Central"""
#	raise ImportError
if [int(v) for v in extension.__version__.split(".")] < [1,1,0]:	  
    print """This module requires at least version 1.1.0 of extension.py.  Please download a newer version from SPSS Developer Central"""
    raise ImportError
from extension import Syntax, Template

if spssaux.GetSPSSMajorVersion() < 16:
    raise ImportError, "This module requires at least SPSS 16"

from warnings import filterwarnings
filterwarnings(action='ignore', module="numpy", category=DeprecationWarning)
filterwarnings(action='ignore', module="scipy", category=DeprecationWarning)



try:
    from scipy import *
except ImportError, e:
    if not e.message.startswith("cannot import name"):
        raise ImportError("""This module requires scipy and numpy.  One or more was not found.  Please download
              from www.scipy.org and try again.  Be sure to get the version matching your Python version.""")

try:
    from numpy import *
    from scipy import linalg, Inf, random, sparse
except:
    print """This module requires scipy and numpy.  One or more was not found.  Please download
              from www.scipy.org and try again.  Be sure to get the version matching your Python version."""
    raise ImportError, "This module requires scipy and numpy."
# end of nontranslatable messages

def Run(args):
    """Called by PLS syntax, with a dictionary of argument values from syntax."""

    # parse and re-package the arguments
    # a variable dictionary is supplied for validation
    args = args["PLS"]
    #print "Arguments:\n", args
    ##debugging
    #try:
        #import wingdbstub
        #if wingdbstub.debugger != None:
            #import time
            #wingdbstub.debugger.StopDebug()
            #time.sleep(2)
            #wingdbstub.debugger.StartDebug()
        #import thread
        #wingdbstub.debugger.SetDebugThreads({thread.get_ident(): 1}, default_policy=0)
        ## for V19 use
        ##    ###SpssClient._heartBeat(False)
    #except:
        #pass
        #enable localization
    global _

    try:
        plsArgs = PLSSyntaxArguments(args)
        plsArgs.parseArguments()
        # normally the extension module would automatically set
        # up the _ function, but PLS is nonstandard so we can't
        # set up an initial default.
        try:
            _("---")
        except:
            def _(msg):
                return msg        

        #dsn = spssaux.GetActiveDatasetName()
        dsn = spss.ActiveDataset()
        if not dsn or dsn == "*": 
            dsn = "PLS_active_data_%s" % str(random.uniform(0,1))
            spss.Submit("DATASET NAME %s WINDOW=ASIS ." % dsn)

        pc = PLSController(dsn, plsArgs)
    except PLSSyntaxException, e:
        proc = PLSRegressionProcedure(None)
        proc.Run(warnings=plsArgs.notifications+[str(e)], parameters=False, vip=False, weights=False, loadings=False, scores=False)
        return

    pls = pc.PLS()
    try:
        pls.plsRegression()
    except Exception, e:
        notify = plsArgs.notifications+[str(e)]
        if pls:
            notify += pls.notifications
        else:
            notify += [_("PLS object could not be created.")]
        proc = PLSRegressionProcedure(None)
        proc.Run(warnings=notify, parameters=False, vip=False, weights=False, loadings=False, scores=False)
        return

#	yvars, xvars, designdsn = PLSController.getDesign(dsn,
#								 dependent=plsArgs.dependent,
#								 categorical=plsArgs.categorical,
#								 refcats = plsArgs.refcats,
#								 factors=plsArgs.by,
#								 covariates=plsArgs.wth,
#								 model=plsArgs.model,
#								 designdsn=plsArgs.dsncases,
#								 idvariable=plsArgs.idvariable)
#	pls = PLSController.PLS(xvars, yvars, plsArgs.latentfactors)
#	pls.plsRegression()

    # to ensure that the correct data set is seen in the Notes table
    spss.Submit("DATASET ACTIVATE %s WINDOW=ASIS ." % dsn)

    # procedure creates pivot table and/or text block output
    proc = PLSRegressionProcedure(pls)

    # to configure default output, change values to False or True as desired
    notify = plsArgs.notifications + pls.notifications
    proc.Run(warnings=notify, parameters=True, vip=True, weights=True, loadings=True, scores=False)

    # arguments determine which datasets are created
    outdata = OutDatasetController(pls, plsArgs)	# cases=plsArgs.dsncases, latentfactors=plsArgs.dsnlatentfactors, predictors=plsArgs.dsnpredictors)
    outdata.Run()

    # graphs are created based on output datasets created above
    plots = PlotController(pls, plsArgs)
    plots.Run()

    # close the design data if not given as an outdataset
    if not plsArgs.dsncases:
        spss.Submit("DATASET CLOSE %s ." % pc.designdsn)
    # restore the original working dataset  crash point?
    spss.Submit("DATASET ACTIVATE %s ." % dsn)
    # WINDOW=ASIS removed to encourage front end to display active state correctly
    if plsArgs.dsncases:
        spss.Submit("DELETE VARIABLES idcase__ .")


class SyntaxArguments(object):
    """Abstract superclass for syntax adapters; also tracks notifications.
    Use the extension module to define the parser argument"""

    def __init__(self, args, parser):
        self.arguments = args
        assert isinstance(parser, Syntax), "parser must be a Syntax object."
        self.parser = parser
        self.params = {}
        self.__notifications = []
        #self.parseArguments()

    def parseArguments(self):
        """Use the parser to process the arguments"""

        self.parser.parsecmd(self.arguments)
        self.params = self.parser.parsedparams
        return self.params

    def __getNotifications(self):
        return self.__notifications

    notifications = property(__getNotifications, None, None, "Error messages to be displayed by the procedure.")

    def appendNotification(self, notify):
        self.__notifications.append(notify)

class PLSSyntaxArguments(SyntaxArguments):
    def __init__(self, args):
        """Do any initialization required before calling super init."""
        # additional initialization here ...

        self.params = {}
        self.dependent = []
        self.categorical = []
        self.refcats = {}
        self.all_level = ""
        self.all_refcat = None

        parser = Syntax([
            Template("", "", var="dependent", ktype="literal", islist=True),
            Template("VARIABLE", "ID", var="idvariable", ktype="existingvarlist"),
            Template("CASES", "OUTDATASET", var="dsncases", ktype="str"),
            Template("LATENTFACTORS", "OUTDATASET", var="dsnlatentfactors", ktype="str"),
            Template("PREDICTORS", "OUTDATASET", var="dsnpredictors", ktype="str"),
            Template("LATENTFACTORS", "CRITERIA", ktype="int", vallist=[1]),
            Template("", "MODEL", var="model", ktype="literal", islist=True)
        ])
        super(PLSSyntaxArguments, self).__init__(args, parser)

    def parseArguments(self):
        params = super(PLSSyntaxArguments, self).parseArguments()
        # further processing is required
        self.parseVariables()
        self.parseSubcommands()
        return params

    def parseSubcommands(self):
        params = self.params
        self.model = params.get("model", [])
        #self.latentfactors = 5    # set default
        self.latentfactors = int(params.get('latentfactors', 5))
        self.idvariable = params.get('idvariable', [''])[0]    # first item in list
        self.dsncases = params.get('dsncases')
        self.dsnlatentfactors = params.get('dsnlatentfactors')
        self.dsnpredictors = params.get('dsnpredictors')

    def parseVariables(self):
        """separate tokenlist into dependent, BY, and WITH; 
        also expand TO, respond to MLEVEL and REFERENCE
        """

        tokenList = self.params["dependent"]
        tokenUp = [token.upper() for token in tokenList]
        # find every instance of 'TO'
        toIndices = [i for i, token in enumerate(tokenUp) if token == 'TO']
        try:
            toRanges = [(tokenList[i-1],tokenList[i+1]) for i in toIndices]
        except:
            #print "Variable list: %s" % " ".join(tokenList)
            #assert False, "Illegal syntax: TO must be preceded and followed by valid variable names."
            raise PLSSyntaxException(_("Illegal syntax: TO must be preceded and followed by valid variable names"))
        if toRanges:
            varDict = spssaux.VariableDict()
            #assert varDict, "TO could not be expanded: variable dictionary not available."
            if not varDict:
                raise PLSSyntaxException(_("TO could not be expanded: variable dictionary not available."))
            try:
                toExpanded = [varDict.range(start, end) for start, end in toRanges]
                toExpanded = [to[1:-2] for to in toExpanded]
                tokens = []
                for i, to in zip(toIndices, toExpanded):
                    tokenList[i] = toExpanded
                    tokenList = listify(tokenList)
                    #print tokenList
            except:
                #assert False, "TO could not be expanded"
                raise PLSSyntaxException(_("TO could not be expanded"))
        try:
            byindex = tokenUp.index('BY')
            by = set(tokenList[byindex:])
        except:
            byindex = len(tokenList)
            by = set()
        try:
            withindex = tokenUp.index('WITH')
            wth = set(tokenList[withindex:])
        except:
            withindex = len(tokenList)
            wth = set()
        varlist = tokenList[:min(byindex, withindex)]
        vars = set(varlist)
        if byindex < withindex:
            by = set(tokenList[byindex:withindex])    #by.difference(wth)
        else:
            wth = set(tokenList[withindex:byindex])    #wth.difference(by)
#        wth = wth.difference(by)
#        print wth
#        by = by.difference(wth)
#        print by
#        vars = vars.difference(by.union(wth))
        # extra fidgeting to avoid case-sensitivity
        wth = wth.difference(set(tokenList[withindex:withindex+1]))    # ['WITH']
        by = by.difference(set(tokenList[byindex:byindex+1]))        # ['BY']
        # keep them in order; only add to list once
        self.wth = []
        for w in tokenList[withindex:]:
            if w in wth:
                self.wth.append(w)
                wth.discard(w)
        self.by = []
        for b in tokenList[byindex:]:
            if b in by:
                self.by.append(b)
                by.discard(b)
#        wth = [w for w in tokenList[withindex:] if w in wth]
#        by = [b for b in tokenList[byindex:] if b in by]
#        print wth
#        print by        
        vars = [v for v in varlist if v in vars]
        self.processVariableList(vars)    # sets vars, categorical, refcat
#        self.by = by
#        self.wth = wth

    def processVariableList(self, search):
        """Check for variables follwed by MLEVEL and/or REFERENCE, add them to categorical list"""

        if len(search) == 0:
            return
        var = search[0]
        varall = (var.upper() == "ALL")
        if not varall:
            self.dependent.append(var)
        search = search[1:]
        search, mlevel = self.__getValueForKeyword(search, "MLEVEL")
        search, refcat = self.__getValueForKeyword(search, "REFERENCE")
        # in case reference appears before mlevel, i.e. they are found out of order
        if refcat:
            if mlevel is None:
                search, mlevel = self.__getValueForKeyword(search, "MLEVEL")
            if mlevel is None:
                self.appendNotification(_("Illegal syntax: REFERENCE=%s encountered after variable %s, without MLEVEL.  This value will be ignored.") % (refcat, var))
            elif  mlevel.upper() == "S":
                self.appendNotification(_("Illegal syntax: REFERENCE=%s encountered after variable %s, declared Scale by MLEVEL.  This value will be ignored.") % (refcat, var))
        if mlevel is not None:
            if mlevel.upper() in ("N", "O"):
                if varall:
                    self.all_level = mlevel
                    self.all_refcat = refcat
                else:
                    self.categorical.append(var)
                    cat = refcat
                    if refcat is None: cat = -1
                    elif refcat.upper() == "FIRST": cat = 0
                    elif refcat.upper() == "LAST": cat = -1
                    else: cat = refcat
                    self.refcats[var.lower()] = cat
            elif mlevel.upper() == "S":
                # could check that the variable is not a string here
                # postpone to getDesign, validate all variables
                pass
            else:
                self.appendNotification(_("Illegal syntax: MLEVEL=%s encountered after variable %s. Legal values are N, O, or S. MLEVEL will be ignored.") % (mlevel, var))
        self.processVariableList(search)

    def __getValueForKeyword(self, search, keyword):
        if len(search) > 2:
            if search[0].upper() == keyword:
                if search[1] == "=":
                    return search[3:], search[2]
                else:
                    self.appendNotification(_("Illegal syntax: %s encountered after variable %s, without required =.") % (keyword, var))
                    return search[1:], None
        return search, None        


class PLSSyntaxException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)

class PLSController(object):
    def __init__(self, dsn, args):
        self.arguments = args
        self.forgiving = False
        self.notifications = []
        self.dsn = dsn
        self.dependent = listify(args.dependent)
        self.categorical = listify(args.categorical)
        self.refcats = args.refcats
        self.factors = listify(args.by)
        self.covariates = listify(args.wth)
        self.model = listify(args.model)
        self.latentfactors = args.latentfactors
        self.designdsn = args.dsncases
        self.idvariable = args.idvariable
        self.yvars = []
        self.xvars = []
        self.weight = ""
        self.split = []

        #try:
#		self._validateSubcommands()
        self._validateArguments()
        self._getDesign()
#		# easier to unpack args here so they will be locals()
#						    dsn=self.dsn,
#						    dependent=self.dependent, 
#							categorical=self.categorical, 
#							refcats = self.refcats, 
#							factors=self.factors, 
#							covariates=self.covariates, 
#							model=self.model, 
#							designdsn=self.designdsn, 
#							idvariable=self.idvariable)

    def _validateArguments(self):
        args = self.arguments

        unique, dup = PLSController._removeDuplicates(self.dependent)
        if dup:
            args.appendNotification(_("Duplicated variables %s removed from dependent variable list.") % ", ".join(dup))
            self.dependent = unique
        unique, dup = PLSController._removeDuplicates(self.factors)
        if dup:
            args.appendNotification(_("Duplicated variables %s removed from factor list.") % ", ".join(dup))
            self.factors = unique
        unique, dup = PLSController._removeDuplicates(self.covariates)
        if dup:
            args.appendNotification(_("Duplicated variables %s removed from covariate list.") % ", ".join(dup))
            self.covariates = unique

        dependent = set(self.dependent)
        factors = set(self.factors)
        covariates = set(self.covariates)

        if not dependent:
            raise PLSSyntaxException(_("There must be at least one dependent variable!"))
        dup = dependent.intersection(factors)
        for d in dup:
            args.appendNotification(_("PLS: Dependent variable %s removed from factor list.") % d)
            #self.factors.remove(d)
        unique, dup = PLSController._removeDuplicates(self.factors, list(dup))
        self.factors = unique													  

        if dup: factors = set(unique)
        dup = dependent.intersection(covariates)
        for d in dup:
            args.appendNotification(_("PLS: Dependent variable %s removed from covariate list.") % d)
            #self.covariates.remove(d)
        unique, dup = PLSController._removeDuplicates(self.covariates, list(dup))
        self.covariates = unique			

        if dup: covariates = set(self.covariates)
        if not factors.union(covariates):
            raise PLSSyntaxException(_("There must be at least one independent variable!"))

        dup = factors.intersection(covariates)
        if dup:
            raise PLSSyntaxException(_("Factor %s should not appear in covariate list") % ", ".join([d for d in dup]))
        if self.latentfactors <= 0:
            raise PLSSyntaxException(_("The number of latent factors to extract must be greater than zero"))
        if self.idvariable in dependent:
            raise PLSSyntaxException(_("The ID variable was found in the list of dependent variables."))
        if self.idvariable in factors:
            raise PLSSyntaxException(_("The ID variable was found in the list of factors."))
        if self.idvariable in covariates:
            raise PLSSyntaxException(_("The ID variable was found in the list of covariates."))
        if args.all_level or args.all_refcat:
            raise PLSSyntaxException(_("PLS: The ALL keyword is not supported."))

        varDict = spssaux.VariableDict()
        invalid = []
        allvariables = self.dependent + self.factors + self.covariates
        if self.idvariable:
            allvariables.append(self.idvariable)

        for v in allvariables:
            if not PLSController._isValid(v, varDict):
                invalid.append(v)
        if invalid:
            if len(invalid) == 1 :
                invalidvars = _("Variable %s does not exist.") % ", ".join(invalid)
            else:
                invalidvars = _("Variables %s do not exist.") % ", ".join(invalid)
            raise PLSSyntaxException(invalidvars)

        if not self.designdsn:
            self.designdsn = "%s_design" % self.dsn
            self.designdsn = self.designdsn.strip('$')

        self.weight = spss.GetWeightVar()
        if self.weight is not None:
            raise PLSSyntaxException(_("Error: The dataset is weighted, but this procedure does not support weights."))

        self.split = spss.GetSplitVariableNames()	#spssaux.GetDatasetInfo("SplitFile")
        if self.split:
            raise PLSSyntaxException(_("Split File is not supported."))		

    @staticmethod
    def _isValid(variable, varDict):
        try:
            varDict[variable]
            return True
        except:	#ValueError
            return False

    @staticmethod
    def _removeDuplicates(variables, duplicates=[]):
        vars = []
        dups = duplicates[:]
        for v in variables:
            if v not in dups:
                if v in vars:
                    dups.append(v)
                else:
                    vars.append(v)
        return vars, dups

    def _getDesign(self):	# , dsname, dependent, categorical=[], refcats = {}, factors="",
                            #	covariates="", model="", designdsn=None, idvariable=""):
        """Build and execute the UNIANOVA design

        dependent variables may be declared categorical
        categorical variables in any list are added to BY
        factors are always added to BY
        covariates are added to WITH unless categorical
        TO will be expanded here also
        """

        # for convenient use by locals()
        args = self.arguments
        dsn=self.dsn
        dependent=self.dependent
        categorical=self.categorical 
        refcats = self.refcats
        factors=self.factors
        covariates=self.covariates
        model=self.model
        designdsn=self.designdsn
        idvariable=self.idvariable
        weight = self.weight
        split = self.split

        vars = dependent+factors+covariates
        if idvariable:
            vars.append(idvariable)
        varDict = spssaux.VariableDict(vars)

        try:
            vartypes = spssaux.GetVariableTypesList([varDict.VariableIndex(var) for var in vars])
        except:
            # redundant or impossible, should have been checked by _validateArguments
            raise PLSSyntaxException(_("Variable %s not found.") % var)
### UNIANOVA will now save outfiles with long string variables correctly 2007/07/06

        stringvars = [var for var, vartype in zip(vars, vartypes) if vartype > 0]
        setcat = set(categorical)
        setcat = setcat.difference(set(listify(idvariable)))
        stringNotCat = set(stringvars).difference(setcat)
        if stringNotCat:
            sncdep = stringNotCat.intersection(set(dependent))
            if sncdep:
                args.appendNotification(_("Warning: String variable %s found without MLEVEL, or with MLEVEL=S. It will be treated as Nominal.") % ", ".join(sncdep))
            sncwith = stringNotCat.intersection(set(covariates))
            if sncwith:
                if self.forgiving:
                    args.appendNotification(_("Warning: String variable %s found after WITH. It will be treated as if following BY.") % ", ".join(sncfactor))
                    covariates.remove(sncwith)
                    factors.extend(sncwith)
                else:
                    raise PLSSyntaxException(_("Warning: String variable %s found after WITH.  String values must follow BY."))
            # add misplaced string variables to categorical
            setcat = setcat.union(stringNotCat)

        byvars = [dep for dep in dependent if dep in setcat]
        byvars += factors
        # undocumented feature: categorical covariates (instead of factors)
        byvars += [cov for cov in covariates if cov in setcat]
        catlist = [catvar.lower() for catvar in byvars]
        byvallabdict = {}
        if byvars:
            byvardict = spssaux.VariableDict(byvars)
            for by in byvars:
                try:
                    byvallabdict[by] = spssaux.GetValueLabels(byvardict[by])
                except:
                    # there were no value labels
                    pass

        selectvars = []	#dependent
        selectvars += byvars[:]
        if byvars:
            byvars.insert(0, "BY")
            byvars.append("\n")
        byvars = "\n".join(textwrap.wrap(" ".join(byvars), 150))

        withvars = [dep for dep in dependent if not dep in setcat]
        # undocumented feature: categorical covariates (instead of factors)
        withvars += [cov for cov in covariates if cov not in setcat]
        if args.dsncases or idvariable:
            idcase = "COMPUTE idcase__ = $casenum .\nEXECUTE ."
        else:
            idcase = ""
        if idcase:
            withvars += ["idcase__"]	# to allow matching by case number

        selectvars += withvars[:]
        if withvars:
            withvars.insert(0, "WITH")
            withvars.append("\n")
            withvars = "\n".join(textwrap.wrap(" ".join(withvars), 150))

        selectvars = [var for var in selectvars if var not in stringvars]
        selectvars = "\n".join(textwrap.wrap(", ".join(selectvars), 150))

        if model: model = " ".join(dependent + model)
        else: model = " ".join(dependent + factors + covariates)

        allvars = spssaux.GetVariableNamesList()
        if not withvars:
            withvars = ""
        suppressTag = "suppress_all"
        cmds = """DATASET DECLARE %(designdsn)s .
OMS SELECT ALL EXCEPT=WARNINGS /DESTINATION VIEWER=NO /TAG='%(suppressTag)s' .
COMPUTE dummy__ = 1.0 .
%(idcase)s
TEMPORARY.
SELECT IF (NMISS(%(selectvars)s)=0).
UNIANOVA
                     dummy__
                     %(byvars)s %(withvars)s  /OUTFILE = DESIGN(%(designdsn)s)
                     /INTERCEPT = EXCLUDE
                     /DESIGN %(model)s .
*DATASET ACTIVATE %(dsn)s WINDOW=ASIS .
DELETE VARIABLES dummy__ .
DATASET ACTIVATE %(designdsn)s WINDOW=ASIS .
OMSEND TAG='%(suppressTag)s'. """ % locals()

        try:
            spss.SetOutput("off")
            spss.Submit(cmds)
            spss.SetOutput("on")
        except:
            raise PLSSyntaxException(_("""A problem was encountered while executing the following syntax.\n
%s""") % cmds)

        spss.SetOutput("on")
        names = spssaux.GetVariableNamesList()
        labels = spssaux.GetVariableLabelsList()
        labeldict = dict(zip(names, labels))

        if idcase:	# and idvariable not in names:
            setvars = set(allvars)
            setnames = set(names)
            #print "Set(Vars):", setvars
            #print "Set(Names):", setnames
            rename = setnames.intersection(setvars)
            rename = rename.difference(set(["idcase__"]))
            #print "Rename:", rename
            renvars = " ".join(rename)
            setdrop = setvars.difference(setnames.union(set([idvariable, "idcase__"])))
            #print setdrop
            dropren = " ".join(["d%s" % i for i in xrange(len(rename))])
            dropvars = " ".join(setdrop)
            idvarcmds = """*OMS /DESTINATION VIEWER=NO /TAG='%(suppressTag)s' .
MATCH FILES
                                  /FILE=*
                                  /FILE=%(dsn)s
                                  /RENAME (%(renvars)s = %(dropren)s)
                                  /DROP= %(dropren)s %(dropvars)s
                                  /BY  idcase__ .
EXECUTE.
DELETE VARIABLES idcase__ .
*OMSEND TAG='%(suppressTag)s' .""" % locals()
            try:
                #print idvarcmds
                spss.SetOutput("off")
                spss.Submit(idvarcmds)
                spss.SetOutput("on")
            except:
                raise PLSSyntaxException(_("Problem while trying to add ID variable %s.\n%s") % (idvariable, idvarcmds))


        # special handling if there is a variable named P1 already
        # if there is, there will be a design variable labelled P1
        start = PLSController._P1_avoid(names, labels, dependent[0])
        end = len(names)
        designvars = [(names[i], labels[i]) for i in xrange(start, end)]

        designdict = dict(designvars)
        desi = [(name, PLSController._parselabel(label)) for name, label in designvars]
        # now find the dependent variables e.g. P1, ...
        deplower = [dep.lower() for dep in dependent]
        depvars = [name for name, label in desi if ((len(label)==1) and (label[0][0].lower() in deplower))]
        #print depvars
        catdesi = [(name, tuple(label)) for name, label in desi if (len(label)==1) and (label[0][0].lower() in catlist)]
        refcatdict = {}
#		# keep the name of the last value encountered for each categorical variable

        # build a dictionary indexed by original variable name,
        # values are tuples (new variable name, category label)
        # e.g. ("P11", "label")
        catdict = {None:[]}	# simplifies lookup logic below
        labeldict = {None:[]}
        #original = ''
        for name, label in catdesi:
            original = label[0][0].lower()
            lab = label[0][1]
            var = catdict.get(original)
            # if var is already in the dictionary, add the new category to the list
            if var:
                catdict[original].append(name)
                labeldict[original].append(lab)
            else:	# start a new list
                catdict[original] = [name]
                labeldict[original] = [lab]
            # keep the name of the last value encountered for each categorical variable
            refcatdict[original] = name	# overwrite previous

        refcatvars = []
        for original, name in refcatdict.iteritems():
            cats = catdict.get(original)
            labels = labeldict.get(original)
            # check if there is a user-specified reference category
            ref = refcats.get(original, -1)
            if isinstance(ref, basestring):
                # it must be a custom category...
                try:
                    catLabel = byvallabdict[original][ref]
                    if catLabel:
                        index = labels.index(catLabel)
                        refcatvars.append(cats[index])
                    else:
                        args.appendNotification(_("Unable to locate reference category for variable %s. The last category will be used.") % var)
                        refcatvars.append(cats[-1])
                except:
                    # if the variable is numeric may need to fidget
                    # find values, labels of original var
                    numcats = [float(label) for label in labels]
                    numref = float(ref)
                    diff = [abs(numcat - numref) for numcat in numcats]
                    mindiff = min(diff)
                    if mindiff < 1e-6:
                        index = diff.index(mindiff)
                        refcatvars.append(cats[index])
                    else:
                        args.appendNotification(_("Unable to locate reference category for variable %s. The last category will be used.") % var)
                        refcatvars.append(cats[-1])
            else:	# FIRST implies 0, LAST implies -1
                try:
                    refcatvars.append(cats[ref])
                except:
                    args.appendNotification(_("Unable to locate reference category for variable %s. The last category will be used.") % var)
                    refcatvars.append(cats[-1])

        refcatlabels = set([label[0] for name, label in desi if (name in refcatvars)])

        desi0 = [(name, labels) for name, labels in desi if not set(labels).intersection(refcatlabels)]
        # temporary measure to ignore weight variable
        if weight:
            if weight in (dependent + factors + covariates):
                args.appendNotification(_("PLS: weight variable %s is present in the model, but treated as an ordinary variable.") % weight)

        labels = [(name, "_".join(labels[0])) for name, labels in desi0]
        yvars = [name for name in depvars if name not in refcatvars]
        xvars = [name for name, labels in desi0 if name not in depvars]
        self.yvars = yvars
        self.xvars = xvars
        self.designdsn = designdsn
        return yvars, xvars, designdsn

    @staticmethod
    def _parselabel(label):
        label = [lab.strip("[]") for lab in label.split("]*[")]
        label = [lab.split("=") for lab in label]
        label = [(lab[0], "=".join(lab[1:])) for lab in label]
        label = tuple(label)		
        return label

    @staticmethod
    def _P1_avoid(names, labels, dependent):
        try:
            p1index = labels.index("P1")
            if names[p1index][0] != "P": p1index = False
            # design variable should be named P followed by 1 or more digits...	
            # could check to make sure next char is a digit also
        except:
            p1index = False
        if p1index:	# there was a variable named P1, find the dependent more carefully
            startcandidates = [name for name in names if name[:3] == "P1_"]
            startcandidates = [name for name in startcandidates  if PLSController._parselabel(labels[names.index(name)])[0][0] == dependent ]
            if len(startcandidates) > 0:
                start = names.index(startcandidates[0])
            else:
                raise PLSSyntaxException(_("Ambiguity caused by a variable named P1."))
        else:
            start = names.index("P1")
        return start

    def PLS(self):
        """Invoke PartialLeastSquares Class factory for instantiating PLS objects.

        This is a bridge between SPSS and NumPy/SciPy.
        This function gets data from an SPSS cursor, and uses it
        to populate SciPy matrix objects.  The PLS object returned
        does not depend on SPSS in any way, only SciPy.
        """
        xvars = self.xvars
        yvars = self.yvars
        d = self.latentfactors
        return PartialLeastSquares.PLS(xvars, yvars, d)		

class PartialLeastSquares(object):
    def __init__(self, xvars, yvars, X, Y, d, xlabels, ylabels, weight=None, split=[]):
        # tsplit file unsupported
        assert not split, "Split File operation is not supported"
        self.__notifications = []
        self.xvars = xvars
        self.yvars = yvars
        self._X = X
        self._Y = Y
        # computed later, retain user-requested value as well
        self._d = d
        self.xlabels = xlabels
        self.ylabels = ylabels
        xN, xn = X.shape
        self.N = xN
        self.n = xn
        yN, ym = Y.shape
        self.m = ym
        assert  xN == yN, "Incommensurate matrices"
        self.d = min(d, xn, xN)
        self.p = None
        self.q = None
        self.P = None
        self.Q = None
        self.T = None
        self.U = None
        self.C = None
        self.W = None
        self.c = None
        self.w = None
        self.u = None
        self.t = None
        self.E = X.copy()
        self.F = Y.copy()
        self.xmean, self.xsd, foo, foo = self.zscore(self.E)
        self.ymean, self.ysd, foo, foo = self.zscore(self.F)
        self._Xz = self.E.copy()
        self._Yz = self.F.copy()
        self.converge = [1e308]*4
        self.intercept = None
        self.B = None
        self.varx = trace(self._Xz.T * self._Xz)
        self.vary = trace(self._Yz.T * self._Yz)
        self.ssx = None
        self.ssy = None
        self.vip = None

    @staticmethod
    def PLS(xvars, yvars, d):
        """Class factory to instantiate PartialLeastSquares objects.

        This is a bridge between SPSS and NumPy/SciPy.
        This function gets data from an SPSS cursor, and uses it
        to populate SciPy matrix objects.  The PLS object returned
        does not depend on SPSS in any way, only SciPy.		
        """
        try:
            numx = len(xvars)
            numy = len(yvars)
            alloriginalvars = yvars + xvars
            vardict = spssaux.VariableDict(alloriginalvars)
            curs = spssdata.Spssdata(indexes=alloriginalvars,   omitmissing=True)
            if len(alloriginalvars)  != curs.numvars:  #undefined variable(s)?
                raise AttributeError, _("Undefined variable name was specified: ") + " ".join(list(set(alloriginalvars) - set(curs.namelist)))
            xlabels = [vardict.VariableLabel(var) for var in xvars]
            xlabels = [xlab if xlab else var for xlab, var in zip(xlabels, xvars)]
            ylabels = [vardict.VariableLabel(var) for var in yvars]
            ylabels = [ylab if ylab else var for ylab, var in zip(ylabels, yvars)]

            data = mat(curs.fetchall())
            Ymat = mat(take(data, indices= range(0,numy), axis=1))
            Xmat = mat(take(data, indices = range(numy, numx+numy), axis=1))
            curs.CClose()
        except linalg.LinAlgError:
            print _("PLS result cannot be computed due to singularity")
            curs.CClose()
            # TODO: should really just return None
            raise
        try:
            # TODO: support weight
            # TODO: support split
            pls = PartialLeastSquares(xvars, yvars, Xmat, Ymat, d, xlabels, ylabels, weight=None, split=[])
        except:
            pls = None
        return pls

    def plsRegression(self, converge=1e-15):
        if self.m == 1:
            for i in xrange(self.d):
                self.NIPALS()
                rq = self.c.T * self._eigenprob() * self.c
                if rq < converge:
                    self.d = i
                    self.appendNotification(_("No more than %s latent factors can be extracted.") % i)
                    break
                else:
                    p, q = self.deflate()
        else:
            for i in xrange(self.d):
                rq = self.extractFactor(converge)
                if rq < converge:
                    self.d = i
                    self.appendNotification(_("No more than %s latent factors can be extracted.") % i)
                    break
                else:
                    p, q = self.deflate()	

        B = self.W * (self.P.T * self.W).I * self.C.T
        B = multiply(1.0/matrix(self.xsd).T, B)
        B = multiply(B, matrix(self.ysd))
        #print "X standard deviations:\n", Xsd
        #print "Y standard deviations:\n", Ysd

        self.intercept = self.ymean - self.xmean*B
        self.B = B
        self.vip = self.calculateVIP()

    @staticmethod
    def unit(x):
        return x / linalg.norm(x)

    @staticmethod	
    def zscore(A, minstd=0.):
        """standardize columns to mean 0, std 1. 
        Return vectors of means and standard deviations, a list of columns with nonzero variance, and a list of columns
        with standard deviation <= minstd
        If a column standard deviation is below the threshold, it is not changed."""

        cols = A.shape[1]
        means = r_[cols*[0.0]]
        stds = r_[cols*[0.0]]
        nonzerovarvars = []
        zerovarvars = []
        for col in range(cols):
            means[col] = A[:,col].mean()
            stds[col] = A[:,col].std()
            if stds[col] > minstd:
                nonzerovarvars.append(col)
                for i in range(A.shape[0]):
                    A[i,col] = (A[i,col] - means[col]) /stds[col]
            else:
                zerovarvars.append(col)
        return means, stds, nonzerovarvars, zerovarvars

    def extractFactor(self, converge=1e-16, c=None):
        """Extract a single latent factor."""
        if c is None:
            c, lamb = self.eigenvector(converge)
            if lamb < converge:
                return lamb
            self.c = c	# probably not needed
        for i in xrange(100):
            conv0 = matrix(self.converge)
            self.NIPALS()
            if self.convergence(converge):
                break
            A = self._eigenprob()
        return self.c.T * A * self.c

    @staticmethod	
    def extractEigenvector(A, iterates=100, converge=1e-16, powerIterates=3, powerConverge=1e-10):
        n, m = A.shape
        assert n == m, "Square matrix required"
        x, lamb = PartialLeastSquares.extractEigenvectorPowerMethod(A, powerIterates, powerConverge)	
        x, lamb = PartialLeastSquares.extractEigenvectorRayleighQuotientIteration(A, x, lamb, iterates=20, converge=1e-7)
        return (x, lamb)

    @staticmethod	
    def extractEigenvectorPowerMethod(A, iterates=1, converge=1e-6):
        n, m = A.shape
        assert n == m, "Square matrix required"
        x0 = mat([1.0]*n,dtype=float64).T
        x0 = PartialLeastSquares.unit(x0)
        x0 = A*x0
        lamb = 0.0
        delta = linalg.norm(x0, Inf)
        x = x0
        i = 0
        while delta > converge and i < iterates:
            x = A*x0
            lamb = x0.T*x	# = x0.T*A*x0
            x = x/linalg.norm(x)
            #print x-x0, lamb
            delta = linalg.norm(x - x0, Inf)	# L1 norm, (?) or L2
            x0 = x
            i += 1
        return (x, lamb)

    @staticmethod	
    def extractEigenvectorRayleighQuotientIteration(A, x, lamb, iterates=20, converge=1e-7):
        n, m = A.shape
        assert n == m, "Square matrix required"
        if (n,m) ==(1,1):
            return (mat([1.0],dtype=float64), A)
        delta = 1e8
        i = 0
        x = x/linalg.norm(x)	# just to be sure
        while delta > converge and i < iterates:
            if (n,m) == (1,1):
                w = mat([1.0],dtype=float64)
            else:
                # The linalg.cg routine was deprecated somewhere between numpy 1.0 and 1.3, but
                # the sparse.linalg.cg routine does not exist in some earlier versions, so try the newer
                # version first; then fall back if necessary; then fail if that, too, does not work.
                # v 1.3.0 has a bug in the deprecation handler that results in a bad call to warnings.warn
                # with display of a message about expecting a string or buffer object.
                try:
                    from scipy.sparse.linalg.isolve import cg
                except:
                    try:
                        from sparse.linalg import cg
                    except:
                        from linalg import cg  # give up if this fails
                w, info = cg(A - multiply(lamb,identity(n)), x, xtype=0)	# was: multiply(lamb,identity(n))
                w = mat(w,dtype=float64)
            # what is going wrong when A is 1x1?  i.e. A - lamb*I = 0
            # then eigvector is 1
            if w[0,0]*x[0,0] < 0:
                w = -w
            # Rayleigh Quotient = w.T*A*w/w.T*w
            try:
                w = w.T/linalg.norm(w)
            except:
                w = x
            lamb = w.T*A*w	# omit dividing by norm since w is a unit vector
            #lamb = lamb[0][0]
            delta = linalg.norm(w - x, Inf)	# L1 norm, (?) or L2
            #print "RQI:",i, delta, lamb
            x = w
            i += 1
        return (x, lamb)	

    def _calculateSumsOfSquares(self):
        """Assumes plsRegression has been called..."""
        # this can only be right when called at the end of deflate()
        # compute sums of squares explained by regression
        tTt = (self.t.T * self.t)
        ssx = tTt * (self.p.T * self.p)
        ssy = tTt * (self.c.T * self.c)
        self.ssx = self._concatenateColumn(self.ssx, ssx)
        self.ssy = self._concatenateColumn(self.ssy, ssy)

    def calculateVIP(self):
        # W_star = W*(P.T*W).I
        W = self.W
        W = W * (self.P.T * W).I	# really W*

        vip = power(W, 2)
        vip = matrix(vip.real)
        #vip = vip * self.ssy.T	# (n*d) * (d*1) = (n*1)
        # for now just use lists and matrix multiplication to sum
        ssy = self.ssy.tolist()
        ssy = ssy[0]
        ssk = []
        for k in xrange(1,self.d+1):
            ssk.append(ssy[:k] + [0.0]*(self.d-k))
        ssk = matrix(ssk)		# (d*d)
        vip = vip * ssk.T		# (n*d)
        vip = self.n*vip/cumsum(self.ssy)
        vip = sqrt(vip)
        vip = vip.real
        return vip	

    def _eigenprob(self):
        # for now always take m as the smallest dimension
        Y = self.F
        X = self.E
        return Y.T * X * X.T * Y

    def eigenvector(self, converge=1e-10):
        v, lamb = self.extractEigenvector(self._eigenprob(), converge=converge)
        if lamb < converge:
            self.appendNotification(_("X variance exhausted"))
        return v, lamb

    def NIPALS(self):
        X = self.E
        Y = self.F
        c = self.c
        if c is None:
            N, m = Y.shape
            c = PartialLeastSquares.unit(mat([1]*m))
            c = c.T
        u = Y*c
        w = X.T*u	#   Xd.T*(Yd*c)
        w = w/linalg.norm(w)
        t = X*w
        c = Y.T*t
        c = c/linalg.norm(c)
        self._checkConvergence(c, u, w, t, 2)
        self.t = t
        self.c = c
        self.u = u
        self.w = w
        return

    def _checkConvergence(self, c, u, w, t, p=2):
        converge = []
        if self.c is None or self.u is None or self.w is None or self.t is None:
            return [1e308] * 4
        for v0, v1 in zip((self.c, self.u, self.w, self.t), (c,u,w,t)):
            converge.append(self.distance(v0, v1, p))
        self.converge = converge
        return converge

    def convergence(self, epsilon=1e-15):
        for x in self.converge:
            if abs(x) > epsilon:
                return False
        return True

    @staticmethod
    def distance(x0, x1, p=Inf):
        # probably use a try block instead
        if (x0 is not None) and (x1 is not None):
            delta = linalg.norm(x1 - x0, p)
        else:
            delta = 1e308
        return delta

    def _concatenateColumn(self, V, v):
        if V is not None:
            return concatenate((V, v), 1)
        else:
            return v

    def deflate(self, t=None):
        if t:
            pass	# probably remove this when done testing
        else:
            t = self.t
        X = self.E
        Y = self.F
        Nx, n = X.shape
        Ny, m = Y.shape
        Nt, o = t.shape
        #print "Deflate matrices: ", Nx, n, Ny, m, Nt, o
        assert Nx == Nt, "Matching dimensions required"
        tnormsq = (t.T*t)[0,0]
        p = X.T*t/tnormsq
        c = Y.T*t/tnormsq
        X1 = X - t*p.T
        Y1 = Y - t*c.T
        u = Y*c/linalg.norm(c)	# ToDo: check u scale-invariant
        q = Y.T*u/(u.T*u)
        w = X.T*u	#   Xd.T*(Yd*c)
        w0 = w	# in case W should be un-normed
        w = w/linalg.norm(w)
        self.E = X1
        self.F = Y1
        self.p = p
        self.q = q
        self.c = c
        self.w = w
        self.T = self._concatenateColumn(self.T, t)	# append to get [ T | t ]
        self.P = self._concatenateColumn(self.P, p)
        self.Q = self._concatenateColumn(self.Q, q)
        self.U = self._concatenateColumn(self.U, u)
        self.C = self._concatenateColumn(self.C, c)
        self.W = self._concatenateColumn(self.W, w)	# w normed, w0 not
        self._calculateSumsOfSquares()
        return (p, q)

    def _predictions(self):
        Xsd = mat(self.xsd)
        Ysd = mat(self.ysd)
        #err = 0
        intercept = self.ymean - self.xmean*self.B
        xhat = multiply((self.T * self.P.T) , Xsd) + self.xmean
        yhat = self._X * self.B + intercept
        return xhat, yhat

    @staticmethod
    def _distanceToModel(A, N, d):
        d2 = sum((N/float(N-d-1)) * matrix(power(A, 2)), axis=1)
        return sqrt(d2).real

    # TODO: use a common interface for notifications	
    def __getNotifications(self):
        return self.__notifications

    notifications = property(__getNotifications, None, None, "Error messages to be displayed by the procedure.")

    def appendNotification(self, notify):
        self.__notifications.append(notify)


class OutDatasetController(object):
    def __init__(self, pls, plsArgs=None, cases=None, latentfactors=None, predictors=None):
        self.pls = pls
        self.plsArgs = plsArgs
        if plsArgs:
            cases = plsArgs.dsncases
            latentfactors = plsArgs.dsnlatentfactors
            predictors = plsArgs.dsnpredictors
        if cases:
            OutDatasetPredResid(cases, pls, predicted=True, residuals=True, scores=True, distances=True)
        if latentfactors:
            OutDatasetWeightsLoadings(latentfactors, pls)
        if predictors:
            OutDatasetPredictors(predictors, pls)

    def Run(self):
        pass

class OutDataset(object):
    def __init__(self, datasetname, pls):
        self.datasetname = datasetname
        self.pls = pls

    def createDictionary(self):
        assert False, "OutDataset is an abstract superclass, createDictionary must be overridden."


    def _appendVarsToCursor(self, curs, vars, varlabel, rootname, missing=None):
        """
        curs is a Spssdata cursor
        vars should be a list of variables or iterable
        varlabel should have a single %s substitution for the variable
        rootname should be a valid variable name
        """
        newvars = []
        for var in vars:
            #lab = self.vardict.VariableLabel(var)
            #if not lab: lab = var
            vlbl = varlabel % var	#lab	# was var
            vname = self._mungeLabel("%s%s" % (rootname, var))
            if len(vname) > 64:
                vname = "%s%s" % (rootname, vars.index(var)+1)
            newvars.append(vname)
            if missing:
                missinglabel = {missing[0]:"."}
            else:
                missinglabel = None
            curs.append(spssdata.vdef(vname, 0, vlbl, valuelabels=missinglabel, missingvalues=missing))  #define new variable		
        return newvars

    def _mungeLabel(self, label):
        """Replace space with underscore, * with by """
        import re
        label = label.replace(r"]*[", "_BY_")
        label = label.replace("[", "")
        label = label.replace("]", "")
        label = re.sub("[^a-zA-Z0-9_.@]", "_", label)
        label = re.sub("[_.]+$", "", label)
        #print label
        return label

    def _appendToCases(self, curs, matrices):
        # current implementation:
        # convert each matrix to list of lists
        # that is convert list of matrices to list of list of lists
        # append rows into one long list
        # TODO: find a more efficient implementation
        # walk through rows of each matrix
        # convert one row at a time to list
        # append lists
        mlist = [m.tolist() for m in matrices]
        for i, case in enumerate(curs):
            #yhatvalue = self._X[i] * self.B * self.ysd + intercept
            casevalues = []
            for ml in mlist:
                casevalues.extend(ml[i])
            curs.casevalues(casevalues)
            # could check X - xhat against E, Y - yhat against F here

    def _appendNewCases(self, curs, matrices, varnames=None):
        # current implementation:
        # convert each matrix to list of lists
        # that is convert list of matrices to list of list of lists
        # append rows into one long list
        # walk through rows of each matrix
        # convert one row at a time to list
        # append lists
        mlist = [m.tolist() for m in matrices]
        for i in xrange(matrices[0].shape[0]):	# assume there is at least one matrix
            #yhatvalue = self._X[i] * self.B * self.ysd + intercept
            casevalues = []
            if varnames:
                casevalues.extend([varnames[i]])
            for ml in mlist:
                casevalues.extend(ml[i])
            for j, value in enumerate(casevalues):
                curs.appendvalue(j, value)
            curs.CommitCase()
            # could check X - xhat against E, Y - yhat against F here

class OutDatasetPredResid(OutDataset):				
    def __init__(self, datasetname, pls, predicted=True, residuals=True, scores=True, distances=False):
        super(OutDatasetPredResid, self).__init__(datasetname, pls)
        #self.pls = pls
        curs = spssdata.Spssdata(indexes=pls.yvars + pls.xvars, dataset=datasetname, omitmissing = True, accessType='w')
        matrices = self.createDictionary(curs, predicted, residuals, scores, distances)
        self._appendToCases(curs, matrices)
        curs.CClose()

    def createDictionary(self, curs, predicted=False, residuals=False, scores=False, distances=False):
        matrices = []
        xhat = None
        yhat = None
        if predicted:
            vlbl = _("PLS predicted values %s ")
            self._appendVarsToCursor(curs, self.pls.xlabels, vlbl, "pred_x_")
            self._appendVarsToCursor(curs, self.pls.ylabels, vlbl, "pred_y_")
            xhat, yhat = self.pls._predictions()
            matrices.append(xhat)
            matrices.append(yhat)
        if residuals:
            vlbl = _("PLS residual values %s ")
            self._appendVarsToCursor(curs, self.pls.xlabels, vlbl, "resid_x_")
            self._appendVarsToCursor(curs, self.pls.ylabels, vlbl, "resid_y_")
            if xhat == None or yhat == None:
                xhat, yhat = self._predictions()
            matrices.append(self.pls._X - xhat)
            matrices.append(self.pls._Y - yhat)
        if scores:
            vlbl = _("PLS scores %s ")
            self._appendVarsToCursor(curs, xrange(1,self.pls.d+1), vlbl, "scores_x_")
            self._appendVarsToCursor(curs, xrange(1,self.pls.d+1), vlbl, "scores_y_")
            matrices.append(self.pls.T)
            matrices.append(self.pls.U)
        if distances:
            vlbl = _("Distance to Model %s")
            curs.append(spssdata.vdef("D_Mod_X", 0, vlbl % " - X"))
            curs.append(spssdata.vdef("D_Mod_Y", 0, vlbl % " - Y"))
            dmodx = self.pls._distanceToModel(self.pls.E, self.pls.N, self.pls.d)
            dmody = self.pls._distanceToModel(self.pls.F, self.pls.N, self.pls.d)
            matrices.append(dmodx)
            matrices.append(dmody)

        curs.commitdict()
        return matrices

class OutDatasetWeightsLoadings(OutDataset):		
    def __init__(self, datasetname, pls, weights=True, loadings=True):
        super(OutDatasetWeightsLoadings, self).__init__(datasetname, pls)
        curs = spssdata.Spssdata(indexes=[], dataset=None, omitmissing = True, accessType='n')
        matrices = self.createDictionary(curs, weights, loadings)
        self._appendNewCases(curs, matrices, varnames=self.pls.xlabels+self.pls.ylabels)
        curs.CClose()
        spss.Submit("DATASET NAME %s WINDOW=ASIS ." % datasetname)

    def createDictionary(self, curs, weights=True, loadings=True):
        matrices = []
        curs.append(spssdata.vdef("variable", max([len(vname)for vname in (self.pls.xlabels + self.pls.ylabels)]), "Variable"))
        if weights:
            # use W* or W_star not W
            # W_star = W*(P.T*W).I
            W = self.pls.W
            W = W * (self.pls.P.T * W).I	# here W is really W*
            vlbl = _("PLS weights %s ")
            self._appendVarsToCursor(curs, xrange(1,self.pls.d+1), vlbl, "weight")						
            matrices.append(concatenate((W, self.pls.C), axis=0))
        if loadings:
            vlbl = _("PLS loadings %s ")
            self._appendVarsToCursor(curs, xrange(1,self.pls.d+1), vlbl, "loading")						
            matrices.append(concatenate((self.pls.P, self.pls.Q), axis=0))
        curs.commitdict()
        return  matrices

class OutDatasetPredictors(OutDataset):					
    def __init__(self, datasetname, pls, parameters=True, vip=True):
        super(OutDatasetPredictors, self).__init__(datasetname, pls)
        curs = spssdata.Spssdata(indexes=[], dataset=None, omitmissing = True, accessType='n')
        matrices = self.createDictionary(curs, parameters, vip)
        self._appendNewCases(curs, matrices, varnames=["(Constant)"] + self.pls.xlabels)
        curs.CClose()
        spss.Submit("DATASET NAME %s WINDOW=ASIS ." % datasetname)			

    def createDictionary(self, curs, parameters=True, vip=True):
        matrices = []
        curs.append(spssdata.vdef("variable", max([len(vname)for vname in ["(Constant)"] + self.pls.xlabels]), "Variable"))
        if parameters:
            vlbl = _("PLS parameters %s ")
            self._appendVarsToCursor(curs, self.pls.ylabels, vlbl, "B_")						
            matrices.append(concatenate((self.pls.intercept, self.pls.B)))
        if vip:
            vlbl = _("PLS VIP %s ")
            # set vipvars to have user missing = -99999
            sysmiss = None	#-99999
            vipvars = self._appendVarsToCursor(curs, xrange(1,self.pls.d+1), vlbl, "VIP_", missing=[-99999])						
            matrices.append(concatenate((matrix([None]*self.pls.d), self.pls.vip)))
        curs.commitdict()
        return matrices

class SPSSProcedure(object):
    def __init__(self, procedure):
        self.procedure = procedure
        self._started = False

    def start(self):
        """Only tell SPSS to start a procedure once."""
        try:
            if not self._started:
                spss.StartProcedure(self.procedure)
            self._started = True
        except:
            print _("Warning: procedure %s could not be started.") % self.procedure
            self._started = False

    def matrixToTable(self,
                      theMatrix, 
                      title,
                      caption="", 
                      rowdim="Rows",
                      rowlabels=None,
                      coldim="Cols",
                      collabels=None):
        """Translate the matrix into a simple pivot table.

        Procedure must have been started already.
        """
        # automatic labels for experimentation
        nrows, ncols = theMatrix.shape
        if rowlabels: pass
        else: rowlabels = ["%s" % r for r in xrange(1, nrows+1)]
        if collabels: pass
        else: collabels = ["%s" % c for c in xrange(1, ncols+1)]
        cells = theMatrix.tolist()
        #spss.StartProcedure(procedure)
        try:
            table = spss.BasePivotTable(title, title)
            table.SetDefaultFormatSpec(spss.FormatSpec.Coefficient,3)
            if caption: table.Caption(caption)
            # ecn139660: p.t. api will fail if cells is not flat and there is only one column
            table.SimplePivotTable(rowdim,rowlabels,coldim,collabels,flatten(cells))
        except:
            print _("Procedure %s could not produce table %s.") % (self.procedure, title)
            #raise:

    def textBlock(self, title, lines=[]):
        if self._started and lines:
            if isinstance(lines, basestring):
                text = lines
            elif isinstance(lines, (list, tuple)):
                text = "\n".join(lines)
            else:
                text = lines	# try it and see
            try:
                block = spss.TextBlock(title, text)
#			# there appears to be a problem with append
#			# each line starts a new TextBlock... WAS...
#			try:
#				text = spss.TextBlock(title, lines[0])
#				for line in lines[1:]:
#					text.append(line)
            except:
                print _("Error trying to add text block %s:\n%s.") % (title, "\n".join(linelist))

    def end(self):
        if self._started:
            try:
                spss.EndProcedure()
            except:
                print _("Error trying to end procedure %s.") % self.procedure
        self._started = False

class PLSRegressionProcedure(SPSSProcedure):
    def __init__(self, pls):
        super(PLSRegressionProcedure, self).__init__("PLS Regression")
        self.pls = pls	# TODO: check that pls is actually a PartialLeastSquares object

    def outputVariance(self):
        pls = self.pls

        v = pls.ssx / pls.varx

        v = concatenate((v, cumsum(pls.ssx) / pls.varx))
        v = concatenate((v, pls.ssy / pls.vary))

        r2 = cumsum(pls.ssy) / pls.vary

        df = matrix([1.0]*v.shape[1])
        df = cumsum(df)

        N1 = pls.N - 1.0
        r2adj = 1.0 - multiply((1.0 - r2),N1)/(N1 - df)

        v = concatenate((v, r2))
        v = concatenate((v, r2adj))

        self.matrixToTable(v.T,
                           title=_("Proportion of Variance Explained"), 
                           caption="",
                           rowdim=_("Latent Factors"),
                           rowlabels=None,
                           coldim=_("Statistics"),
                           collabels=[_("X Variance"), _("Cumulative X Variance"), _("Y Variance"), _("Cumulative Y Variance (R-square)"), _("Adjusted R-square")])

    def outputParameters(self):
        self.matrixToTable(concatenate((self.pls.intercept, self.pls.B)),
                           title=_("Parameters"), 
                           caption="",
                           rowdim=_("Independent Variables"),
                           rowlabels=[_("(Constant)")] + self.pls.xlabels,
                           coldim=_("Dependent Variables"),
                           collabels=self.pls.ylabels)

    def outputVIP(self):
        self.matrixToTable(self.pls.vip, 
                           title=_("Variable Importance in the Projection"), 
                           caption=_("Cumulative Variable Importance"),
                           rowdim=_("Variables"),
                           rowlabels=self.pls.xlabels,
                           coldim=_("Latent Factors"),
                           collabels=None)

    def outputWeights(self):
        # use W* or W_star not W
        # W_star = W*(P.T*W).I
        W = self.pls.W
        W = W * (self.pls.P.T * W).I	# here W is really W*
        self.matrixToTable(concatenate((W, self.pls.C)), 
                           title=_("Weights"), 
                           caption="",
                           rowdim=_("Variables"),
                           rowlabels=self.pls.xlabels+self.pls.ylabels,
                           coldim=_("Latent Factors"),
                           collabels=None)

    # N.B. should be very similar to Weights
    def outputLoadings(self):
        self.matrixToTable(concatenate((self.pls.P, self.pls.Q)),
                           title=_("Loadings"), 
                           caption="",
                           rowdim=_("Variables"),
                           rowlabels=self.pls.xlabels+self.pls.ylabels,
                           coldim=_("Latent Factors"),
                           collabels=None)

    # TODO: rework this to have a second dimension, 
    # with categories "X-scores" and "Y-scores"
    # i.e. no longer use .simpleOutputTable
    def outputScores(self):
        scorelabels = [_("X-score %s") % i for i in xrange(1, self.pls.d+1)]
        scorelabels += [_("Y-score %s") % i for i in xrange(1, self.pls.d+1)]
        self.matrixToTable(concatenate((self.pls.T, self.pls.U), axis=1), 
                           title=_("Scores"), 
                           caption=_("Standardized Scores"),
                           rowdim=_("Cases"),
                           rowlabels=None,	# TODO: id variable
                           coldim=_("Latent Factor Scores"),
                           collabels=scorelabels)

    def Run(self, warnings=[], parameters=True, vip=True, weights=True, loadings=True, scores=False):
        self.start()
        self.textBlock(_("Warnings"), warnings)
        if self.pls:
            self.outputVariance()
            if parameters: self.outputParameters()
            if vip: self.outputVIP()
            if weights: self.outputWeights()
            if loadings: self.outputLoadings()
            if scores: self.outputScores()
        self.end()

def listify(x):
    """Convenience function to allow strings or lists to be used as arguments.

    If a string is given, it will be tokenized into a list using whitespace as
    separator.  If a list or tuple is given, its elements will be processed.
    If anything else is given, convert it to a string, and then try to make
    the result into a list.
    """
    if not x:
        return []
    if isinstance(x, basestring):
        xlist = x.split()
    elif isinstance(x, (list, tuple)):
        xlist = []
        for l in x:
            xlist += listify(l)
    else:
        xlist = listify(str(x))
    return xlist

class PlotController(object):
    def __init__(self, pls, plsArgs=None, cases=None, latentfactors=None, predictors=None, color=None, maxCases=2000):
        self.d = pls.d
        self.cases = None
        self.factors = None
        self.predictors = None
        if plsArgs:
            cases = plsArgs.dsncases
            latentfactors = plsArgs.dsnlatentfactors
            predictors = plsArgs.dsnpredictors
            if plsArgs.dsncases:
                if plsArgs.categorical:
                    color = plsArgs.categorical[0]
                elif plsArgs.by:
                    color = plsArgs.by[0]
                else:
                    color = ""
            self.cases = CasePlot(pls.d, cases, pls.N, maxCases, color, plsArgs.idvariable)
            self.splom = SPLOM(pls.d, cases, pls.N, maxCases, maxVariables=10, color=color, id="")
        if latentfactors:
            self.factors = FactorPlot(pls.d, latentfactors, pls.n + pls.m, maxCases)
        if predictors:
            self.predictors = VIPPlots(pls.d, predictors, pls.n, maxCases)
            # note switch of N to number of variables instead of number of cases

    def Run(self):
        if self.predictors:
            self.predictors.plot()
        if self.cases:
            if self.d == 1:
                self.cases.plot("scores_x_1", "scores_y_1", _("X-Score 1"), _("Y-Score 1"), _("Regression Plot"))
            if self.d == 2:
                variables = ["scores_x_%s" % i for i in xrange(1,self.d+1)]
                variableLabels = [_("X-Score %s") % i for i in xrange(1,self.d+1)]
#				# temporary test
                yvariables = ["scores_y_%s" % i for i in xrange(1,self.d+1)]
                yvariableLabels = [_("Y-Score %s") % i for i in xrange(1,self.d+1)]
                self.splom.plot(variables, variableLabels, yvariables, yvariableLabels, _("Regression Plot: Y-Scores vs. X-Scores"))
                self.cases.plot("scores_x_1", "scores_x_2", _("X-Score 1"), _("X-Score 2"), _("Score Plot"))
            if self.d > 2:
                variables = ["scores_x_%s" % i for i in xrange(1,self.d+1)]
                variableLabels = [_("X-Score %s") % i for i in xrange(1,self.d+1)]
                # temporary test
                yvariables = ["scores_y_%s" % i for i in xrange(1,self.d+1)]
                yvariableLabels = [_("Y-Score %s") % i for i in xrange(1,self.d+1)]
                self.splom.plot(variables, variableLabels, yvariables, yvariableLabels, _("Regression Plot: Y-Scores vs. X-Scores"))
                self.splom.plot(variables, variableLabels, title=_("Scores"))

        if self.factors:
            if self.d > 1:
                self.factors.plot("weight1", "weight2", _("Weight 1"), _("Weight 2"), title=_("Factor Weights 2 vs. 1"))
            if self.d > 2:
                self.factors.plot("weight1", "weight3", _("Weight 1"), _("Weight 3"), title=_("Factor Weights 3 vs. 1"))
                self.factors.plot("weight2", "weight3", _("Weight 2"), _("Weight 3"), title=_("Factor Weights 3 vs. 2"))


class Plot(object):
    def __init__(self, d, dataset, N=0, maxCases=2000):
        self.d = d
        self.dataset = dataset
        self.N = N	# N=0 implies no limit
        self.maxCases = maxCases		

    def plot(self):
        assert False, "Plot object is an abstract superclass, plot method must be overridden."

class CasePlot(Plot):
    def __init__(self, d, dataset, N=0, maxCases=2000, color="", id="", panel=None):
        super(CasePlot, self).__init__(d, dataset, N, maxCases)
        self.color = color
        self.panel = panel
        self.id = id

    def plot(self, x, y, xlabel="", ylabel="", title = None):
        if title is None:
            title = _("Scores")
        dataset = self.dataset
        if not dataset:
            return
        if self.N > self.maxCases:
            print _("PLS plots are limited to %s cases, but there are %s cases in the data.  No plot will be produced.") % (self.maxCases, self.N)
            return
        c = self.color
        id = self.id
        if not xlabel: xlabel = _("PLS %s") % x
        if not ylabel: ylabel = _("PLS %s") % y
        if c:
            colordata = """
                                  DATA: color=col(source(s), name("%s"), unit.category())
""" % c
            colorguidescale = """
                                        GUIDE: legend(aesthetic(aesthetic.color.exterior), label("%s"))
                                        SCALE: cat(aesthetic(aesthetic.color.exterior))
""" % c
            colorelement = ", color.exterior(color)"
        else:
            colordata = ""
            colorguidescale = ""
            colorelement = ""
        if id:
            iddata = """
                               DATA: id=col(source(s), name("%s"))
""" % id
            idlabel = ", label(id)"
        else:
            iddata = ""
            idlabel = ""
        graphlabel = """LABEL="PLS: %s" """ % title
        ggraph = """DATASET ACTIVATE %(dataset)s WINDOW=ASIS .
* Chart Builder.
GGRAPH
                       /GRAPHDATASET NAME="graphdataset"
                       VARIABLES=%(x)s %(y)s %(c)s %(id)s
                       MISSING=LISTWISE REPORTMISSING=NO
                       /GRAPHSPEC SOURCE=INLINE %(graphlabel)s.
BEGIN GPL
                       SOURCE: s=userSource(id("graphdataset"))
                       DATA: x=col(source(s), name("%(x)s"))
                       DATA: y=col(source(s), name("%(y)s"))%(colordata)s%(iddata)s
                       GUIDE: axis(dim(1), label("%(xlabel)s"))
                       GUIDE: axis(dim(2), label("%(ylabel)s"))%(colorguidescale)s
                       GUIDE: text.title(label("%(title)s"))
                       ELEMENT: point(position(x*y)%(colorelement)s%(idlabel)s)
END GPL."""

        spss.Submit(ggraph % locals())

class SPLOM(Plot):
    def __init__(self, d, dataset, N=0, maxCases=2000, maxVariables=10, color="", id="", panel=None):
        super(SPLOM, self).__init__(d, dataset, N, maxCases)
        self.maxVariables = maxVariables
        self.color = color
        self.id = id
        self.panel = panel

    def plot(self, variables, variableLabels, yvariables=[], yvariableLabels=[], title=None):
        if title is None:
            title = _("Scores")
        dataset = self.dataset		
        variables = variables[:self.maxVariables]
        yvariables = yvariables[:self.maxVariables]
        vars = " ".join(variables+yvariables)
        c = self.color
        id = self.id
        if not dataset:
            return
        if self.N > self.maxCases:
            print _("PLS plots are limited to %s cases, but there are %s cases in the data.  No plot will be produced.") % (self.maxCases, self.N)
            return
        data = "\n".join([""" DATA: %(var)s=col(source(s), name("%(var)s"))""" % {"var":var} for var in (variables+yvariables)])
        if c:
            colordata = """\n DATA: color=col(source(s), name("%s"), unit.category())""" % c
            colorexterior = """,color.exterior(color)"""
            colorguide = """ GUIDE: legend(aesthetic(aesthetic.color.exterior), label("%s"))""" % c
        else:
            c = ""
            colordata = ""
            colorexterior = ""
            colorguide = ""
        label = "\n".join([""" TRANS: %(var)s_label = eval("%(varlabel)s")""" % {"var":var, "varlabel":lab} for var, lab in zip(variables+yvariables, variableLabels+yvariableLabels)])
        coords = "\n +".join(["""%(var)s/%(var)s_label""" % {"var":var} for var in variables])
        if yvariables:
            ycoords = "\n +".join(["""%(var)s/%(var)s_label""" % {"var":var} for var in yvariables])
        else:
            ycoords = coords
        if id:
            iddata = """
                               DATA: id=col(source(s), name("%s"))
""" % id
            # make the id variable available, 
            # but don't use it by default
            #idlabel = ", label(id)"
            idlabel = ""
        else:
            iddata = ""
            idlabel = ""
        graphlabel = """LABEL="PLS: %s" """ % title
        ggraph = """DATASET ACTIVATE %(dataset)s WINDOW=ASIS .
GGRAPH
                       /GRAPHDATASET NAME="graphdataset" VARIABLES=%(vars)s %(c)s %(id)s
                       MISSING=LISTWISE REPORTMISSING=NO
                       /GRAPHSPEC SOURCE=INLINE %(graphlabel)s.
BEGIN GPL
                       SOURCE: s=userSource(id("graphdataset"))
%(data)s%(colordata)s%(iddata)s
%(label)s
                       GUIDE: axis(dim(1.1), ticks(null()))
                       GUIDE: axis(dim(2.1), ticks(null()))
                       GUIDE: axis(dim(1), gap(0px))
                       GUIDE: axis(dim(2), gap(0px))%(colorguide)s
                       GUIDE: text.title(label("%(title)s"))
                       SCALE: cat(aesthetic(aesthetic.color.exterior))
                       ELEMENT: point(position((
                       %(coords)s
                       )*(
                       %(ycoords)s
                       ))%(colorexterior)s%(idlabel)s)
END GPL."""
        spss.Submit(ggraph % locals())

class FactorPlot(Plot):
    def __init__(self, d, dataset, N=0, maxCases=2000):
        super(FactorPlot, self).__init__(d, dataset, N, maxCases)

    def plot(self, x, y, xlabel="", ylabel="", min=-1.0, max=1.0, title=None):
        if title is None:
            title = _("Weights")
        dataset = self.dataset
        if not dataset:
            return
        if not xlabel: xlabel = _("PLS %s") % x
        if not ylabel: ylabel = _("PLS %s") % y
        graphlabel = """LABEL="PLS: %s" """ % title
        ggraph = """DATASET ACTIVATE %(dataset)s WINDOW=ASIS .
* Chart Builder.
GGRAPH
                       /GRAPHDATASET NAME="graphdataset" 
                       VARIABLES=%(x)s %(y)s variable
                       MISSING=LISTWISE REPORTMISSING=NO
                       /GRAPHSPEC SOURCE=INLINE %(graphlabel)s.
BEGIN GPL
                       SOURCE: s=userSource(id("graphdataset"))
                       DATA: x=col(source(s), name("%(x)s"))
                       DATA: y=col(source(s), name("%(y)s"))
                       DATA: variable=col(source(s), name("variable"), unit.category())
                       GUIDE: axis(dim(1), label("%(xlabel)s"))
                       GUIDE: axis(dim(2), label("%(ylabel)s"))
                       TRANS: xOrigin = eval(0)
                       TRANS: yOrigin = eval(0)
                       GUIDE: text.title(label("%(title)s"))
                       SCALE: linear(dim(1), min(%(min)s), max(%(max)s))
                       SCALE: linear(dim(2), min(%(min)s), max(%(max)s))
                       ELEMENT: point(position(x*y), label(variable))
                       ELEMENT: edge(position(link.join(xOrigin*yOrigin+x*y)))
END GPL."""
        spss.Submit(ggraph % locals())

class VIPPlot(Plot):
    def __init__(self, d, dataset, N=0, maxCases=2000):
        super(VIPPlot, self).__init__(d, dataset, N, maxCases)

    def plot(self, i, title=None):
        if title is None:
            title= _("Variable Importance") # wait to resolve title until function is called
        dataset = self.dataset
        if not dataset:
            return
        graphlabel = """LABEL="PLS: %s" """ % title
        ggraph = """DATASET ACTIVATE %(dataset)s WINDOW=ASIS .
* Chart Builder.
GGRAPH
                       /GRAPHDATASET NAME="graphdataset" VARIABLES=variable VIP_%(i)s 
                       MISSING=LISTWISE REPORTMISSING=NO
                       /GRAPHSPEC SOURCE=INLINE %(graphlabel)s.
BEGIN GPL
                       SOURCE: s=userSource(id("graphdataset"))
                       DATA: variable=col(source(s), name("variable"), unit.category())
                       DATA: VIP=col(source(s), name("VIP_%(i)s"))
                       GUIDE: axis(dim(1), label("Variable"))
                       GUIDE: axis(dim(2), label("PLS VIP %(i)s"))
                       GUIDE: text.title(label("%(title)s"))
                       SCALE: cat(dim(1))
                       SCALE: linear(dim(2), include(0))
                       ELEMENT: interval(position(variable*VIP), shape.interior(shape.square))
END GPL."""
        spss.Submit(ggraph % locals())


class VIPPlots(Plot):
    def __init__(self, d, dataset, factors=10, N=0, maxCases=2000):
        super(VIPPlots, self).__init__(d, dataset, N, maxCases)
        self.factors = factors

    def plot(self, title=None):
        if title is None:
            title=_("Cumulative Variable Importance")
        dataset = self.dataset
        factors = min(self.factors, self.d, 10)
        vips = ["VIP_%s" % i for i in xrange(1,factors+1)]
        variables = " ".join(vips)
        vipdata = [""" DATA: %(vip)s=col(source(s), name("%(vip)s"))""" % {"vip":vip} for vip in vips]
        vipdata = "\n".join(vipdata)
        vipposition = ["""variable*%(vip)s*1*"%(i)s" """ % {"vip":vip,"i":i} for vip, i in zip(vips, xrange(1, factors+1))]
        vipposition = "+".join(vipposition)
        if not dataset:
            return
        graphlabel = """LABEL="PLS: %s" """ % title
        ggraph = """DATASET ACTIVATE %(dataset)s WINDOW=ASIS .
* Chart Builder.
GGRAPH
                       /GRAPHDATASET NAME="graphdataset" VARIABLES=variable %(variables)s
                       MISSING=LISTWISE REPORTMISSING=NO
                       /GRAPHSPEC SOURCE=INLINE %(graphlabel)s.
BEGIN GPL
                       SOURCE: s=userSource(id("graphdataset"))
                       DATA: variable=col(source(s), name("variable"), unit.category())
%(vipdata)s
                       GUIDE: axis(dim(1), label("Variable"))
                       GUIDE: axis(dim(2), label(""))
                       GUIDE: text.title(label("%(title)s"))
                       SCALE: cat(dim(1))
                       ELEMENT: interval(position(%(vipposition)s), shape.interior(shape.square))
END GPL."""
        spss.Submit(ggraph % locals())

# flatten function to resolve all elements of a list, including sequences, into a a flat list
def flatten(seq):
    """return seq as a flat list

    seq is any sequence object"""

    res = []
    for item in seq:
        if spssaux._isseq(item):     # is this iterable (but not a string)?
            res.extend(flatten(item))
        else:
            res.append(item)
    return res