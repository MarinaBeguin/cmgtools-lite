# USAGE: python impactPlots.py fitresults_poim1_exp0_bbb0.root -o plots/fit/absY/results/2018-12-10 --nuis 'CMS.*' --pois 'Wplus.*left.*'
import ROOT, os, datetime, re, operator, math
from array import array
from subMatrix import niceName
ROOT.gROOT.SetBatch(True)

from make_diff_xsec_cards import get_ieta_ipt_from_process_name
from postFitPlots import prepareLegend

import utilities
utilities = utilities.util()

def niceSystName(label):
    if 'lepScale' in label: niceName = 'lepton scale'
    elif 'OtherBkg' in label: niceName = 'other bkg'
    elif 'pdfs' in label: niceName = 'PDF'
    elif 'binByBinStat' in label: niceName = 'MC statistics'
    elif 'EffStat' in label: niceName = 'efficiency stat. unc.'
    elif 'Fakes' in label: niceName = 'fakes unc.'
    elif 'OtherExp' in label: niceName = 'other experimental unc.'
    elif 'lumi' in label: niceName = 'luminosity'
    elif 'QCDTheo' in label: niceName = '#mu_{F},#mu_{R}, #alpha_{S}'
    elif 'stat' in label: niceName = 'statistical'
    elif 'Total' in label: niceName = 'Total unc.'
    return niceName

def latexLabel(label):
    bin = int(label.split(' ')[-1]) if any(pol in label for pol in ['left','right','long']) else -1
    deltaYW = 0.2 ### should use binningYW.txt, but let's  not make it too complicated
    minY,maxY=bin*deltaYW,(bin+1)*deltaYW
    binLbl = ' {minY}<|Y_\mathrm{{ W }}|<{maxY}'.format(minY=minY,maxY=maxY)
    lblNoBin = ' '.join(label.split(' ')[:-1])
    lblNoBin = lblNoBin.replace('+','^+').replace(' left','_L').replace(' right','_R')
    lblNoBin += binLbl
    return lblNoBin

if __name__ == "__main__":

    ROOT.gStyle.SetOptStat(0)

    from optparse import OptionParser
    parser = OptionParser(usage='%prog fitresults.root [options] ')
    parser.add_option('-o','--outdir',     dest='outdir',     default='',   type='string', help='outdput directory to save the matrix')
    parser.add_option(     '--pois',       dest='pois',       default='',   type='string', help='pois for which you want to show the correlation matrix. comma separated list of regexps')
    parser.add_option(     '--nuis',       dest='nuis',       default='',   type='string', help='nuis for which you want to show the correlation matrix. comma separated list of regexps')
    parser.add_option(     '--nuisgroups', dest='nuisgroups', default='',   type='string', help='nuis groups for which you want to show the correlation matrix. comma separated list of regexps')
    parser.add_option(     '--suffix',     dest='suffix',     default='',   type='string', help='suffix for the correlation matrix')
    parser.add_option(     '--target',     dest='target',     default='mu', type='string', help='target POI (can be mu,xsec,xsecnorm)')
    parser.add_option(     '--zrange',     dest='zrange',     default='', type='string', help='Pass range for z axis as "min,max". If not given, it is set automatically based on the extremes of the histogram')
    parser.add_option(     '--canvasSize', dest='canvasSize', default='', type='string', help='Pass canvas dimensions as "width,height" ')
    parser.add_option(     '--margin',     dest='margin',     default='', type='string', help='Pass canvas margin as "left,right,top,bottom" ')
    parser.add_option(     '--nContours', dest='nContours',    default=51, type=int, help='Number of contours in palette. Default is 51 (let it be odd, so the central strip is white if not using --abs-value and the range is symmetric)')
    parser.add_option(     '--palette'  , dest='palette',      default=0, type=int, help='Set palette: default is a built-in one, 55 is kRainbow')
    parser.add_option(     '--invertPalette', dest='invertePalette' , default=False , action='store_true',   help='Inverte color ordering in palette')
    parser.add_option(     '--parNameCanvas', dest='parNameCanvas',    default='', type='string', help='The canvas name is built using the parameters selected with --nuis or nuisgroups. If they are many, better to pass a name, like QCDscales or PDF for example')
    parser.add_option(     '--abs-value', dest='absValue' , default=False , action='store_true',   help='Use absolute values for impacts (groups are already positive)')
    parser.add_option('-a','--absolute',   dest='absolute',   default=False, action='store_true', help='absolute uncertainty (default is relative)')
    parser.add_option(     '--latex',      dest='latex',      default=False, action='store_true', help='target POI (can be mu,xsec,xsecnorm)')
    parser.add_option('-y','--ybinfile',   dest='ybinfile',   default='',  type='string', help='do 1D summary plot as a function of YW using this file with the yw binning')
    (options, args) = parser.parse_args()

    # palettes:
    # 69 + inverted, using TColor::InvertPalette(), kBeach
    # 70 + inverted, using TColor::InvertPalette(), kBlackBody
    # 107, kCool
    # 57 kBird
    # 55 kRainBow

    ROOT.TColor.CreateGradientColorTable(3,
                                         array ("d", [0.00, 0.50, 1.00]),
                                         ##array ("d", [1.00, 1.00, 0.00]),
                                         ##array ("d", [0.70, 1.00, 0.34]),
                                         ##array ("d", [0.00, 1.00, 0.82]),
                                         array ("d", [0.00, 1.00, 1.00]),
                                         array ("d", [0.34, 1.00, 0.65]),
                                         array ("d", [0.82, 1.00, 0.00]),
                                         255,  0.95)

    if options.absValue:
        ROOT.TColor.CreateGradientColorTable(2,
                                             array ("d", [0.00, 1.00]),
                                             ##array ("d", [1.00, 1.00, 0.00]),
                                             ##array ("d", [0.70, 1.00, 0.34]),
                                             ##array ("d", [0.00, 1.00, 0.82]),
                                             array ("d", [1.00, 1.00]),
                                             array ("d", [1.00, 0.65]),
                                             array ("d", [1.00, 0.00]),
                                             255,  0.95)

    if len(options.nuis) and len(options.nuisgroups):
        print 'You can specify either single nuis (--nuis) or poi groups (--nuisgroups), not both!'
        sys.exit()

    if options.outdir:
        # emanuele: why this?
        #options.outdir = options.outdir + "/" + options.target + "/"
        ROOT.gROOT.SetBatch()
        if not os.path.isdir(options.outdir):
            os.system('mkdir -p {od}'.format(od=options.outdir))
        os.system('cp {pf} {od}'.format(pf='/afs/cern.ch/user/g/gpetrucc/php/index.php',od=options.outdir))

    if len(options.nuis)==0 and len(options.nuisgroups)==0:
        print "Will plot the impact for all the single nuisances. It may be a big matrix"
        nuis_regexps = ['.*']
    else:
        nuis_regexps = list(options.nuis.split(',')) if len(options.nuis) else list(options.nuisgroups.split(','))
        print "Filtering nuisances or nuisance groups with the following regex: ",nuis_regexps

    if len(options.pois)==0:
        pois_regexps = ['.*']
    else:
        pois_regexps = list(options.pois.split(','))
    
    hessfile = ROOT.TFile(args[0],'read')
    valuesAndErrors = utilities.getFromHessian(args[0])

    group = 'group_' if len(options.nuisgroups) else ''
    if   options.target=='xsec':     target = 'pmaskedexp'
    elif options.target=='xsecnorm': target = 'pmaskedexpnorm'
    else:                            target = 'mu'

    if options.ybinfile:
        pois_regexps = ['W{ch}.*{pol}.*'.format(ch=charge,pol=pol) for charge in ['plus','minus'] for pol in ['left','right','long']]

    th2name = 'nuisance_{group}impact_{sfx}'.format(group=group,sfx=target)
    impMat = hessfile.Get(th2name)
    if impMat==None:
        print "ERROR: Cannot find the impact TH2 named ",th2name," in the input file. Maybe you didn't run --doImpacts?\nSkipping."
        sys.exit()
    
    pois = []; pois_indices = []
    for ib in xrange(1,impMat.GetNbinsX()+1):
        for poi in pois_regexps:
            if re.match(poi, impMat.GetXaxis().GetBinLabel(ib)):
                pois.append(impMat.GetXaxis().GetBinLabel(ib))
                pois_indices.append(ib)

    nuisances = []; nuisances_indices = []
    for ib in xrange(1,impMat.GetNbinsY()+1):
        for n in nuis_regexps:
            if re.match(n, impMat.GetYaxis().GetBinLabel(ib)):
                nuisances.append(impMat.GetYaxis().GetBinLabel(ib))
                nuisances_indices.append(ib)

    mat = {}
    for ipoi, poi in enumerate(pois):
        for inuis, nuis in enumerate(nuisances):
            mat[(poi,nuis)] = impMat.GetBinContent(pois_indices[ipoi], nuisances_indices[inuis])

    ## sort the pois and nuisances alphabetically, except for pdfs, which are sorted by number
    pois = sorted(pois, key= lambda x: int(x.split('_')[-1]) if '_Ybin_' in x else 0)
    pois = sorted(pois, key= lambda x: get_ieta_ipt_from_process_name(x) if ('_ieta_' in x and '_ipt_' in x) else 0)
    if len(options.nuisgroups)==0:
        ## for mu* QCD scales, distinguish among muR and muRXX with XX in 1-10
        nuisances = sorted(nuisances, key= lambda x: int(x.replace('pdf','')) if 'pdf' in x else 0)
        nuisances = sorted(nuisances, key= lambda x: int(x.replace('muRmuF','')) if ('muRmuF' in x and x != "muRmuF")  else 0)
        nuisances = sorted(nuisances, key= lambda x: int(x.replace('muR','')) if (''.join([j for j in x if not j.isdigit()]) == 'muR' and x != "muR") else 0)
        nuisances = sorted(nuisances, key= lambda x: int(x.replace('muF','')) if (''.join([j for j in x if not j.isdigit()]) == 'muF' and x != "muF") else 0)
        nuisances = sorted(nuisances, key= lambda x: int(x.split('EffStat')[1]) if 'EffStat' in x else 0)

    #print "sorted pois = ", pois
    #print "\n\nsorted nuisances = ", nuisances

    ch = 1200
    cw = 1200
    if options.canvasSize:
        cw = int(options.canvasSize.split(',')[0])
        ch = int(options.canvasSize.split(',')[1])
    c = ROOT.TCanvas("c","",cw,ch)
    c.SetGridx()
    c.SetGridy()
    if options.nContours: ROOT.gStyle.SetNumberContours(options.nContours)
    if options.palette:   ROOT.gStyle.SetPalette(options.palette)
    if options.invertePalette:    ROOT.TColor.InvertPalette()


    clm = 0.2
    crm = 0.2
    cbm = 0.2
    ctm = 0.1
    if options.margin:
        clm,crm,ctm,cbm = (float(x) for x in options.margin.split(','))
    c.SetLeftMargin(clm)
    c.SetRightMargin(crm)
    c.SetBottomMargin(cbm)
    c.SetTopMargin(ctm)

    ## make the new, smaller TH2F correlation matrix
    nbinsx = len(pois); nbinsy = len(nuisances)
    th2_sub = ROOT.TH2F('sub_imp_matrix', '', nbinsx, 0., nbinsx, nbinsy, 0., nbinsy)
    th2_sub.GetXaxis().SetTickLength(0.)
    th2_sub.GetYaxis().SetTickLength(0.)
    
    if   options.target=='xsec':     target = 'pmaskedexp'
    elif options.target=='xsecnorm': target = 'pmaskedexpnorm'
    else:                            target = 'mu'

    poiName_target = {"mu": "signal strength",
                      "xsec": "cross section",
                      "xsecnorm": "normalized cross section"}
    th2_sub.GetZaxis().SetTitle("impact on POI for {p} {units}".format(units='' if options.absolute else '(%)', p=poiName_target[options.target]))

    ## pretty nested loop. enumerate the tuples
    for i,x in enumerate(pois):
        for j,y in enumerate(nuisances):
            ## set it into the new sub-matrix
            if options.absolute: 
                val = mat[(x,y)]
            else: 
                val = 100*mat[(x,y)]/valuesAndErrors[x+'_'+target][0] if valuesAndErrors[x+'_'+target][0] !=0 else 0.0
            th2_sub.SetBinContent(i+1, j+1, abs(val) if options.absValue else val)
            ## set the labels correctly
            new_x = niceName(x)
            new_y = niceName(y)
            th2_sub.GetXaxis().SetBinLabel(i+1, new_x)
            th2_sub.GetYaxis().SetBinLabel(j+1, new_y)
            

    rmax = max(abs(th2_sub.GetMaximum()),abs(th2_sub.GetMinimum()))
    if not options.absolute: rmax = min(20.,rmax)
    if options.absValue:
        th2_sub.GetZaxis().SetRangeUser(0,rmax)
    else :
        th2_sub.GetZaxis().SetRangeUser(-rmax,rmax)
    if options.zrange:
        rmin,rmax = (float(x) for x in options.zrange.split(','))
        th2_sub.GetZaxis().SetRangeUser(rmin,rmax)
    th2_sub.GetXaxis().LabelsOption("v")
    if options.absolute: 
        ROOT.gStyle.SetPaintTextFormat('1.3f')
        if options.target != "mu":
            ROOT.gStyle.SetPaintTextFormat('.3g')
    else: 
        ROOT.gStyle.SetPaintTextFormat('1.1f')

    if len(pois)<30 and len(nuisances)<30: th2_sub.Draw('colz0 text45')
    else: th2_sub.Draw('colz0')
    if len(nuisances)>30: th2_sub.GetYaxis().SetLabelSize(0.02)

    if options.parNameCanvas: 
        cname = options.parNameCanvas
    else:
        nuisName = 'NuisGroup'+options.nuisgroups if len(options.nuisgroups) else options.nuis
        nuisName = nuisName.replace(',','AND').replace('.','').replace('*','').replace('$','').replace('^','').replace('|','').replace('[','').replace(']','')
        poisName = options.pois.replace(',','AND').replace('.','').replace('*','').replace('$','').replace('^','').replace('|','').replace('[','').replace(']','')
        cname = "{nn}_On_{pn}".format(nn=nuisName,pn=poisName)

    suff = '' if not options.suffix else '_'+options.suffix
    poisNameNice = options.parNameCanvas if len(options.parNameCanvas) else  poisName.replace('(','').replace(')','').replace('\|','or')
    if options.latex:
        txtfilename = 'smallImpacts{rel}{suff}_{target}_{nn}_On_{pn}.tex'.format(rel='Abs' if options.absolute else 'Rel',suff=suff,target=target,i=i,nn=nuisName,pn=poisNameNice)
        if options.outdir: txtfilename = options.outdir + '/' + txtfilename
        txtfile = open(txtfilename,'w')
        txtfile.write("\\begin{tabular}{l "+"   ".join(['r' for i in xrange(th2_sub.GetNbinsX())])+"} \\hline \n")
        txtfile.write('                    ' + " & ".join(['{poi}'.format(poi=latexLabel(th2_sub.GetXaxis().GetBinLabel(i+1))) for i in xrange(th2_sub.GetNbinsX())]) + "\\\\ \\hline \n")
        for j in xrange(th2_sub.GetNbinsY()):
            txtfile.write('{label:<20}& '.format(label=th2_sub.GetYaxis().GetBinLabel(j+1)) + " & ".join(['{syst:^.2f}'.format(syst=th2_sub.GetBinContent(i+1,j+1)) for i in xrange(th2_sub.GetNbinsX())]) + "\\\\ \n")
        txtfile.write("\\end{tabular}\n")
        txtfile.close()
        print "Saved the latex table in file ",txtfilename

    if options.outdir and not options.latex and not options.ybinfile:
        for i in ['pdf', 'png']:
            suff = '' if not options.suffix else '_'+options.suffix
            c.SaveAs(options.outdir+'/smallImpacts{rel}{suff}_{target}_{cn}.{i}'.format(rel='Abs' if options.absolute else 'Rel',suff=suff,target=target,i=i,cn=cname))

        os.system('cp {pf} {od}'.format(pf='/afs/cern.ch/user/g/gpetrucc/php/index.php',od=options.outdir))

    if options.ybinfile:
        ybinfile = options.ybinfile
        ybinfile = open(ybinfile, 'r')
        ybins = eval(ybinfile.read())
        ybinfile.close()

        summaries = {}
        groups = [th2_sub.GetYaxis().GetBinLabel(j+1) for j in xrange(th2_sub.GetNbinsY())]
        for charge in ['plus','minus']:
            for pol in ['left','right', 'long']:
                cp = '{ch}_{pol}'.format(ch=charge,pol=pol)
                for ing,nuisgroup in enumerate(groups):
                    h = ROOT.TH1D(cp+'_'+nuisgroup,'',len(ybins[cp])-1,array('d',ybins[cp]))
                    summaries[(charge,pol,nuisgroup)] = h
                    summaries[(charge,pol,nuisgroup)].SetMarkerSize(2)
                    summaries[(charge,pol,nuisgroup)].SetMarkerColor(utilities.safecolor(ing+1))
                    summaries[(charge,pol,nuisgroup)].SetLineColor(utilities.safecolor(ing+1))
                    summaries[(charge,pol,nuisgroup)].SetLineWidth(2)
                    summaries[(charge,pol,nuisgroup)].GetXaxis().SetRangeUser(0.,3.)
                    summaries[(charge,pol,nuisgroup)].GetXaxis().SetTitle('|Y_{W}|')
                    summaries[(charge,pol,nuisgroup)].GetYaxis().SetRangeUser(5.e-3,500.)
                    summaries[(charge,pol,nuisgroup)].GetYaxis().SetTitle('Relative uncertainty (%)')
                    summaries[(charge,pol,nuisgroup)].GetXaxis().SetTitleSize(0.06)
                    summaries[(charge,pol,nuisgroup)].GetXaxis().SetLabelSize(0.04)
                    summaries[(charge,pol,nuisgroup)].GetYaxis().SetTitleSize(0.06)
                    summaries[(charge,pol,nuisgroup)].GetYaxis().SetLabelSize(0.04)
                    summaries[(charge,pol,nuisgroup)].GetYaxis().SetTitleOffset(0.7)
        for j,nuisgroup in enumerate(groups):
            for i in xrange(th2_sub.GetNbinsX()):
                lbl = th2_sub.GetXaxis().GetBinLabel(i+1)
                charge = 'plus' if '+' in lbl else 'minus'
                pol = lbl.split()[-2]
                ybin = int(lbl.split()[-1])
                summaries[(charge,pol,nuisgroup)].SetBinContent(ybin+1,th2_sub.GetBinContent(i+1,j+1))

        fitErrors = {} # this is needed to have the error associated to the TH2 x axis label
        for i,x in enumerate(pois):
            new_x = niceName(x).replace('el: ','').replace('mu: ','')
            fitErrors[new_x] = 100*abs((valuesAndErrors[x+'_'+target][1]-valuesAndErrors[x+'_'+target][0])/valuesAndErrors[x+'_'+target][0])

        cs = ROOT.TCanvas("cs","",1800,900)
        cs.SetLeftMargin(0.1)
        cs.SetRightMargin(0.05)
        cs.SetBottomMargin(0.15)
        cs.SetTopMargin(0.1)
        cs.SetGridy()
        for charge in ['plus','minus']:
            for ipol,pol in enumerate(['left','right']):
                leg = prepareLegend(xmin=0.5,legWidth=0.40,textSize=0.04)
                leg.SetNColumns(4)
                lat = ROOT.TLatex()
                lat.SetNDC(); lat.SetTextFont(42)
                latBin = ROOT.TLatex()
                latBin.SetNDC(); latBin.SetTextFont(42); latBin.SetTextSize(0.07)
                quadrsum = summaries[(charge,pol,groups[0])].Clone('quadrsum_{ch}_{pol}'.format(ch=charge,pol=pol))
                totalerr = quadrsum.Clone('totalerr_{ch}_{pol}'.format(ch=charge,pol=pol))
                for ing,ng in enumerate(groups):
                    drawopt = 'pl' if ing==0 else 'pl same'
                    summaries[(charge,pol,ng)].Draw(drawopt)
                    if   ng=='binByBinStat': summaries[(charge,pol,ng)].SetMarkerStyle(ROOT.kFullCircle)
                    elif ng=='stat'        : summaries[(charge,pol,ng)].SetMarkerStyle(ROOT.kFullCircle); summaries[(charge,pol,ng)].SetMarkerColor(ROOT.kBlack); summaries[(charge,pol,ng)].SetLineColor(ROOT.kBlack);
                    elif ng=='luminosity'  : summaries[(charge,pol,ng)].SetMarkerStyle(ROOT.kFullSquare)
                    else: summaries[(charge,pol,ng)].SetMarkerStyle(ROOT.kFullTriangleUp+ing)
                    leg.AddEntry(summaries[(charge,pol,ng)], niceSystName(ng), 'pl')
                    # now compute the quadrature sum of all the uncertainties (neglecting correlations among nuis groups)
                    for y in xrange(quadrsum.GetNbinsX()):
                        quadrsum.SetBinContent(y+1,math.hypot(quadrsum.GetBinContent(y+1),summaries[(charge,pol,ng)].GetBinContent(y+1)))
                quadrsum.SetMarkerStyle(ROOT.kFullCrossX); quadrsum.SetMarkerSize(3); quadrsum.SetMarkerColor(ROOT.kBlack); quadrsum.SetLineColor(ROOT.kBlack); quadrsum.SetLineStyle(ROOT.kDashed)
                quadrsum.Draw('pl same')
                # now fill the real total error from the fit (with correct correlations)
                for y in xrange(totalerr.GetNbinsX()):
                    totalerr.SetBinContent(y+1,fitErrors['W{sign} {pol} {bin}'.format(sign='+' if charge is 'plus' else '-',pol=pol,bin=y)])
                totalerr.SetMarkerStyle(ROOT.kFullDoubleDiamond); totalerr.SetMarkerSize(3); totalerr.SetMarkerColor(ROOT.kRed+1); totalerr.SetLineColor(ROOT.kRed+1);
                totalerr.Draw('pl same')
                leg.AddEntry(quadrsum, 'Quadr. sum. impacts', 'pl')
                leg.AddEntry(totalerr, 'Total uncertainty', 'pl')
                leg.Draw('same')
                lat.DrawLatex(0.1, 0.92, '#bf{CMS} #it{Preliminary}')
                lat.DrawLatex(0.8, 0.92, '36 fb^{-1} (13 TeV)')
                latBin.DrawLatex(0.8, 0.2, 'W_{{{pol}}}^{{{chsign}}}'.format(pol=pol,chsign='+' if charge=='plus' else '-'))
                for i in ['pdf', 'png']:
                    suff = '' if not options.suffix else '_'+options.suffix
                    cs.SetLogy()
                    cs.SaveAs(options.outdir+'/ywImpacts{rel}{suff}_{target}_{ch}{pol}.{i}'.format(rel='Abs' if options.absolute else 'Rel',suff=suff,target=target,i=i,ch=charge,pol=pol))

