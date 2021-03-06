# USAGE: python runAllFits.py cards_el el
import os,sys,datetime
from submitToys import makeCondorFile,jobstring_tf


from optparse import OptionParser
parser = OptionParser(usage="%prog [options] cardsDir flavor ")
parser.add_option("-q", "--queue",     dest="queue",  action="store_true",  default=False, help="Run jobs on condor instead of locally");
parser.add_option('-r'  , '--runtime', default=24, type=int, help='New runtime for condor resubmission in hours. default: 24h (combined fits may be long)');
(options, args) = parser.parse_args()

cardsdir = os.path.abspath(args[0])
channel = args[1]
if channel not in ['mu','el','lep']:
    print "Channel must be either mu or el or lep (el-mu combination). Exiting."
    sys.exit()

pois = [('poim1',''),('poim0',' --POIMode none ')]
expected = [('exp1',' -t -1 '),('exp0',' -t 0 ')]
BBBs = [('bbb1',' --binByBinStat --correlateXsecStat '),('bbb0','')]

date = datetime.date.today().isoformat()
absopath  = os.path.abspath('fitsout_'+date)
if options.queue:
    jobdir = absopath+'/jobs/'
    if not os.path.isdir(jobdir):
        os.system('mkdir -p {od}'.format(od=jobdir))
    logdir = absopath+'/logs/'
    if not os.path.isdir(logdir):
        os.system('mkdir -p {od}'.format(od=logdir))
    errdir = absopath+'/errs/'
    if not os.path.isdir(errdir):
        os.system('mkdir -p {od}'.format(od=errdir))
    outdirCondor = absopath+'/outs/'
    if not os.path.isdir(outdirCondor):
        os.system('mkdir -p {od}'.format(od=outdirCondor))

srcfiles = []

for ipm,POImode in pois:
    card = cardsdir+"/W{chan}_card_withXsecMask.hdf5".format(chan=channel) if ipm=='poim1' else cardsdir+'/W{chan}_card.hdf5'.format(chan=channel)
    doImpacts = ' --doImpacts ' if ipm=='poim1' else ''
    for iexp,exp in expected:
        saveHist = ' --saveHists --computeHistErrors '
        for ibbb,bbb in BBBs:
            cmd = 'combinetf.py {poimode} {exp} {bbb} {saveh} {imp} {card} --fitverbose 9'.format(poimode=POImode, exp=exp, bbb=bbb, saveh=saveHist, imp=doImpacts, card=card)
            if options.queue:
                job_file_name = jobdir+'jobfit_{ipm}_{iexp}_{ibbb}.sh'.format(ipm=ipm, iexp=iexp, ibbb=ibbb)
                log_file_name = job_file_name.replace('.sh','.log')
                tmp_file = open(job_file_name, 'w')
                tmp_filecont = jobstring_tf
                tmp_filecont = tmp_filecont.replace('COMBINESTRING', cmd)
                tmp_filecont = tmp_filecont.replace('CMSSWBASE', os.environ['CMSSW_BASE']+'/src/')
                tmp_filecont = tmp_filecont.replace('OUTDIR', absopath)
                tmp_file.write(tmp_filecont)
                tmp_file.close()
                srcfiles.append(job_file_name)
            else:
                print "running ",cmd
                os.system(cmd)
                os.system('mv fitresults_123456789.root fitresults_{ipm}_{iexp}_{ibbb}.root'.format(ipm=ipm, iexp=iexp, ibbb=ibbb))
                print "fit done. Moving to the next one."
                
if options.queue:
    cf = makeCondorFile(jobdir,srcfiles,options, logdir, errdir, outdirCondor)
    subcmd = 'condor_submit {rf} '.format(rf = cf)
    print subcmd

