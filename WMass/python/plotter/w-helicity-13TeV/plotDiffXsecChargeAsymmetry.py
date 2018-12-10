#!/bin/env python

# python w-helicity-13TeV/plotDiffXsecChargeAsymmetry.py -i cards/diffXsec_mu_2018_07_11_group10_coarseBin/ -o plots/diffXsec/chargeAsymmetry/muon/ -c mu -t toys/diffXsec_mu_2018_07_11_group10_coarseBin/toys_comb_WchargeAsymmetry.root -n [--no-group-POI --hessian -s <suffix>]

import ROOT, os, sys, re, array, math

from make_diff_xsec_cards import getDiffXsecBinning
from make_diff_xsec_cards import templateBinning

sys.path.append(os.getcwd() + "/plotUtils/")
from utility import *

ROOT.gROOT.SetBatch(True)

import utilities
utilities = utilities.util()


def getTH1fromTH2(h2D,h2Derr=None,unrollAlongX=True):  # unrollAlongX=True --> select rows, i.e. takes a stripe from x1 to xn at same y, then go to next stripe at next y
    nX = h2D.GetNbinsX()
    nY = h2D.GetNbinsY()
    nbins = nX * nY
    name = h2D.GetName() + "_unrollTo1D" 
    newh = ROOT.TH1D(name,h2D.GetTitle(),nbins,0.5,nbins+0.5)
    if 'TH2' not in h2D.ClassName(): raise RuntimeError, "Calling getTH1fromTH2 on something that is not TH2"
    for i in xrange(nX):
        for j in xrange(nY):
            if unrollAlongX:
                bin = 1 + i + j * nX
            else:
                bin = 1 + j + i * nY
            newh.SetBinContent(bin,h2D.GetBinContent(i+1,j+1))
            if h2Derr: newh.SetBinError(bin,h2Derr.GetBinContent(i+1,j+1))
            else:      newh.SetBinError(bin,h2D.GetBinError(i+1,j+1))
    return newh



if __name__ == "__main__":


    from optparse import OptionParser
    parser = OptionParser(usage='%prog [options]')
    parser.add_option('-i','--input', dest='inputdir', default='', type='string', help='input directory with all the cards inside. It is used to get other information')
    #parser.add_option(     '--no-group-POI', dest='noGroupPOI', default=False , action='store_true', help='Specify that _group_<N>_ is not present in name of POI')
    parser.add_option('-o','--outdir', dest='outdir', default='', type='string', help='output directory to save things')
    parser.add_option('-t','--toyfile', dest='toyfile', default='.', type='string', help='Root file with toys.')
    parser.add_option('-c','--channel', dest='channel', default='', type='string', help='name of the channel (mu or el)')
    parser.add_option('-C','--charge', dest='charge', default='plus,minus', type='string', help='charges to run')
    parser.add_option('-s','--suffix', dest='suffix', default='', type='string', help='Suffix added to output dir (i.e, either to hessian or toys in the path)')
    parser.add_option('-f','--friend', dest='friend', default='', type='string', help='Root file with friend tree containing total xsec (it does not include the outliers). Tree name is assumed to be "toyFriend"')
    parser.add_option('-l','--lumi-norm', dest='lumiNorm', default='-1', type='float', help='If > 0, divide cross section by this factor (lumi in 1/Pb)')
    parser.add_option('-n','--norm-width', dest='normWidth' , default=False , action='store_true',   help='Normalize cross section histograms dividing by bin width')
    parser.add_option(     '--hessian', dest='hessian' , default=False , action='store_true',   help='The file passed with -t is interpreted as hessian: will provide the central value of charge asymmetry but not the uncertainty, and will not plot the differential cross section')
    parser.add_option(     '--fit-data', dest='fitData' , default=False , action='store_true',   help='If True, axis range in plots is customized for data')
    parser.add_option('-e','--expected-toyfile', dest='exptoyfile', default='.', type='string', help='Root file to get expected and make ratio with data (only work with option --fit-data. If SAME, use same file as data and take _gen variables to get the expected')
    (options, args) = parser.parse_args()

    ROOT.TH1.SetDefaultSumw2()
    ROOT.TH1.StatOverflows(True)
    
    channel = options.channel
    if channel not in ["el","mu"]:
        print "Error: unknown channel %s (select 'el' or 'mu')" % channel
        quit()

    charges = [x for x in options.charge.split(',')]
    for c in charges:
        if c not in ["plus", "minus"]:
            print "Error: unknown charge %s (select 'plus' or 'minus' or both separated by comma)" % c
            quit()



    if options.outdir:
        outname = options.outdir
        addStringToEnd(outname,"/",notAddIfEndswithMatch=True)
        if options.hessian: outname = outname + "/hessian"
        else              : outname = outname + "/toys"
        if len(options.suffix): outname = outname + "_" + options.suffix + "/"
        else                  : outname = outname + "/"
        createPlotDirAndCopyPhp(outname)
    else:
        print "Error: you should specify an output folder using option -o <name>. Exit"
        quit()

    if not options.toyfile:
        print "Error: you should specify a file containing the toys using option -t <name>. Exit"
        quit()


    if options.inputdir:
        if not options.inputdir.endswith("/"): options.inputdir += "/"
        basedir = os.path.basename(os.path.normpath(options.inputdir))
        binfile = options.inputdir + "binningPtEta.txt"
        if "_group" in basedir:
            tokens = basedir.split("_")
            for x in tokens:
                if "group" in x:
                    #ngroup = int("".join(str(s) for s in x if s.isdigit()))
                    ngroup = int(x.split("group")[1])
        else:
            ngroup = 1 
    else:
        print "Error: you should specify an input folder containing all the cards using option -i <name>. Exit"
        quit()

    etaPtBinningVec = getDiffXsecBinning(binfile, "gen")
    genBins  = templateBinning(etaPtBinningVec[0],etaPtBinningVec[1])
    netabins = genBins.Neta
    nptbins  = genBins.Npt

    lepton = "electron" if channel == "el" else "muon"
    Wchannel = "W #rightarrow %s#nu" % ("e" if channel == "el" else "#mu")

    hChAsymm = ROOT.TH2F("hChAsymm_{lep}".format(lep=lepton),"Charge asymmetry: {Wch}".format(Wch=Wchannel),
                         genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
    hChAsymmErr = ROOT.TH2F("hChAsymmErr_{lep}".format(lep=lepton),"Charge asymmetry uncertainty: {Wch}".format(Wch=Wchannel),
                            genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
    

    nbins = genBins.Neta * genBins.Npt
    binCount = 1        
    print "Now filling histograms with charge asymmetry"

    f = ROOT.TFile(options.toyfile, 'read')
    tree = f.Get('fitresults')
    if options.friend != "":
        tree.AddFriend('toyFriend',options.friend)

    for ieta in range(1,genBins.Neta+1):
        for ipt in range(1,genBins.Npt+1):
            #print "\rBin {num}/{tot}".format(num=binCount,tot=nbins),
            sys.stdout.write('Bin {num}/{tot}   \r'.format(num=binCount,tot=nbins))
            sys.stdout.flush()
            binCount += 1

            if options.hessian: 
                #central = utilities.getDiffXsecAsymmetryFromHessian(channel,ieta-1,ipt-1,genBins.Neta,ngroup,options.toyfile)
                central = utilities.getDiffXsecAsymmetryFromHessianFast(channel,ieta-1,ipt-1,genBins.Neta,ngroup,
                                                                        nHistBins=2000, minHist=0., maxHist=1.0, tree=tree)
            else:                
                central,up,down = utilities.getDiffXsecAsymmetryFromToysFast(channel,ieta-1,ipt-1,genBins.Neta,ngroup,
                                                                             nHistBins=2000, minHist=0., maxHist=1.0, tree=tree)
                #central,up,down = utilities.getDiffXsecAsymmetryFromToys(channel,ieta-1,ipt-1,genBins.Neta,ngroup,options.toyfile)
                error = up - central
                hChAsymm.SetBinError(ieta,ipt,error)         
                hChAsymmErr.SetBinContent(ieta,ipt,error)
            hChAsymm.SetBinContent(ieta,ipt,central)        
            


    setTDRStyle()

    canvas = ROOT.TCanvas("canvas","",800,700)

    xaxisTitle = 'gen %s |#eta|' % lepton
    yaxisTitle = 'gen %s p_{T} [GeV]' % lepton
    #zaxisTitle = "Asymmetry::%.3f,%.3f" % (hChAsymm.GetMinimum(),hChAsymm.GetMaximum())
    if options.fitData:
        zaxisTitle = "Asymmetry::0.0,0.45"
        if channel == "el": zaxisTitle = "Asymmetry::0.0,0.45"
    else:
        zaxisTitle = "Asymmetry::0.05,0.35"
        if channel == "el": zaxisTitle = "Asymmetry::0.05,0.35"
    drawCorrelationPlot(hChAsymm,
                        xaxisTitle, yaxisTitle, zaxisTitle,
                        hChAsymm.GetName(),
                        "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

    if not options.hessian:

        zaxisTitle = "Asymmetry uncertainty::%.3f,%.3f" % (max(0,0.99*hChAsymmErr.GetMinimum()),min(0.10,1.01*hChAsymmErr.GetMaximum()))
        #zaxisTitle = "Asymmetry uncertainty::0,0.04" 
        drawCorrelationPlot(hChAsymmErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hChAsymmErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        hChAsymmRelErr = hChAsymmErr.Clone(hChAsymmErr.GetName().replace("AsymmErr","AsymmRelErr"))
        hChAsymmRelErr.Divide(hChAsymm)
        hChAsymmRelErr.SetTitle(hChAsymmErr.GetTitle().replace("uncertainty","rel. uncertainty"))
        zaxisTitle = "Asymmetry relative uncertainty::%.3f,%.3f" % (max(0,0.99*hChAsymmRelErr.GetBinContent(hChAsymmRelErr.GetMinimumBin())),
                                                                    min(0.12,1.01*hChAsymmRelErr.GetBinContent(hChAsymmRelErr.GetMaximumBin()))
                                                                    )
        zaxisTitle = "Asymmetry relative uncertainty::0.01,0.3" 
        drawCorrelationPlot(hChAsymmRelErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hChAsymmRelErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)


    else:
        print "You used option --hessian, so I could not plot the error for charge asymmetry (until it is not in the output of combine)."
        #print "You used option --hessian, so I will quit now."
        #print "If you want to plot the differential cross section as well, you can directly use 'w-helicity-13TeV/plotDiffXsecFromFit.py'"
        #quit()
        # stop here with hessian for now
        # for the hessian cross section you can use w-helicity-13TeV/plotDiffXsecFromFit.py


    for charge in charges:

        print ""
        xaxisTitle = 'gen %s |#eta|' % lepton  # it will be modified later, so I have to restore it here


        chargeSign = "+" if charge == "plus" else "-"

        hMu = ROOT.TH2F("hMu_{lep}_{ch}".format(lep=lepton,ch=charge),
                              "signal strength: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                              genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
        hMuErr = ROOT.TH2F("hMuErr_{lep}_{ch}".format(lep=lepton,ch=charge),
                                 "signal strength uncertainty: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                 genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))

        hDiffXsec = ROOT.TH2F("hDiffXsec_{lep}_{ch}".format(lep=lepton,ch=charge),
                              "cross section: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                              genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
        hDiffXsecErr = ROOT.TH2F("hDiffXsecErr_{lep}_{ch}".format(lep=lepton,ch=charge),
                                 "cross section uncertainty: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                 genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
        hDiffXsecNorm = ROOT.TH2F("hDiffXsecNorm_{lep}_{ch}".format(lep=lepton,ch=charge),
                                  "normalized cross section: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                  genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
        hDiffXsecNormErr = ROOT.TH2F("hDiffXsecNormErr_{lep}_{ch}".format(lep=lepton,ch=charge),
                                     "normalized cross section uncertainty: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                     genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))

        nbins = genBins.Neta * genBins.Npt
        binCount = 1        
        print "Now filling histograms with differential cross section (charge = %s)" % charge


        denExpression = ""
        
        if not options.hessian:
            if options.friend != "":
                denExpression = "totxsec_" + charge
            else:
                denExpression = utilities.getDenExpressionForNormDiffXsec(channel, charge, genBins.Neta,genBins.Npt, ngroup)

        central = 0
        error   = 0

        for ieta in range(1,genBins.Neta+1):
            for ipt in range(1,genBins.Npt+1):

                #print "\rBin {num}/{tot}".format(num=binCount,tot=nbins),
                sys.stdout.write('Bin {num}/{tot}   \r'.format(num=binCount,tot=nbins))
                sys.stdout.flush()
                binCount += 1

                # signal strength
                if options.hessian:                    
                    central = utilities.getSignalStrengthFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                         nHistBins=100, minHist=0.5, maxHist=1.5, tree=tree)                    
                    error = utilities.getSignalStrengthFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                       nHistBins=200, minHist=0.0, maxHist=1., tree=tree, getErr=True)                    
                else:
                    central,up,down = utilities.getSignalStrengthFromToysFast(channel,charge,
                                                                              ieta-1,ipt-1,genBins.Neta,genBins.Npt,
                                                                              ngroup, nHistBins=200, minHist=0.5, maxHist=1.5, tree=tree)
                    error = up - central
                hMu.SetBinContent(ieta,ipt,central)        
                hMu.SetBinError(ieta,ipt,error)         
                hMuErr.SetBinContent(ieta,ipt,error)
                
                # normalized cross section
                if options.hessian:                    
                    central = utilities.getNormalizedDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                             nHistBins=2000, minHist=0., maxHist=200., tree=tree)                    
                    error = utilities.getNormalizedDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                           nHistBins=2000, minHist=0., maxHist=10., tree=tree, getErr=True)                    
                else:
                    central,up,down = utilities.getNormalizedDiffXsecFromToysFast(channel,charge,
                                                                                  ieta-1,ipt-1,genBins.Neta,genBins.Npt,
                                                                                  ngroup,denExpression, nHistBins=1000, minHist=0., maxHist=0.1, tree=tree)
                    error = up - central
                hDiffXsecNorm.SetBinContent(ieta,ipt,central)        
                hDiffXsecNorm.SetBinError(ieta,ipt,error)         
                hDiffXsecNormErr.SetBinContent(ieta,ipt,error)
                
                # unnormalized cross section
                if options.hessian:
                    central = utilities.getDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                   nHistBins=2000, minHist=0., maxHist=200., tree=tree)                    
                    error = utilities.getDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                 nHistBins=2000, minHist=0., maxHist=200., tree=tree, getErr=True)                    
                else:                
                    central,up,down = utilities.getDiffXsecFromToysFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                        nHistBins=2000, minHist=0., maxHist=200., tree=tree)
                    error = up - central
                hDiffXsec.SetBinContent(ieta,ipt,central)        
                hDiffXsec.SetBinError(ieta,ipt,error)         
                hDiffXsecErr.SetBinContent(ieta,ipt,error)




        if options.normWidth:
            hDiffXsec.Scale(1.,"width")
            hDiffXsecErr.Scale(1.,"width")
            hDiffXsecNorm.Scale(1.,"width")
            hDiffXsecNormErr.Scale(1.,"width")

        if options.lumiNorm > 0:
            scaleFactor = 1./options.lumiNorm
            hDiffXsec.Scale(scaleFactor)
            hDiffXsecErr.Scale(scaleFactor)
            # do not divide the normalized cross section, the scaling factor is already removed
            #hDiffXsecNorm.Scale(scaleFactor)
            #hDiffXsecNormErr.Scale(scaleFactor)
            
        hDiffXsecRelErr = hDiffXsecErr.Clone(hDiffXsecErr.GetName().replace('XsecErr','XsecRelErr'))
        hDiffXsecRelErr.Divide(hDiffXsec)
        hDiffXsecRelErr.SetTitle(hDiffXsecErr.GetTitle().replace('uncertainty','rel.unc.'))

        hDiffXsecNormRelErr = hDiffXsecNormErr.Clone(hDiffXsecNormErr.GetName().replace('XsecNormErr','XsecNormRelErr'))
        hDiffXsecNormRelErr.Divide(hDiffXsecNorm)
        hDiffXsecNormRelErr.SetTitle(hDiffXsecNormErr.GetTitle().replace('uncertainty','rel.unc.'))

        # now starting to draw the cross sections

        zaxisTitle = "Signal strength #mu::0.98,1.02"
        if options.hessian: zaxisTitle = "Signal strength #mu::0.995,1.005"
        drawCorrelationPlot(hMu,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hMu.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas,palette=55)

        zaxisTitle = "uncertainty on signal strength #mu::0.0,0.25"
        if options.hessian: zaxisTitle = "uncertainty on signal strength #mu::0.0,0.25"
        drawCorrelationPlot(hMuErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hMuErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas,palette=55)


        if options.fitData:
            if charge == "plus": zmin,zmax = 30,130
            else:                zmin,zmax = 20,110
        else:
            if charge == "plus": zmin,zmax = 30,120
            else:                zmin,zmax = 25,95
        #zaxisTitle = "d#sigma / d#etadp_{T} [pb/GeV]::%.3f,%.3f" % (0.9*hDiffXsec.GetMinimum(),hDiffXsec.GetMaximum())
        zaxisTitle = "d#sigma / d#etadp_{T} [pb/GeV]::%.3f,%.3f" % (zmin,zmax)
        drawCorrelationPlot(hDiffXsec,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsec.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        if options.fitData:
            if charge == "plus": zmin,zmax = 0.5,4.5
            else:                zmin,zmax = 0.5,3.5
        else:
            if charge == "plus": zmin,zmax = 0.5,4.5
            else:                zmin,zmax = 0.5,3.5
        zaxisTitle = "uncertainty on d#sigma / d#etadp_{T} [pb/GeV]::%.3f,%.3f" % (0.9*hDiffXsecErr.GetMinimum(),min(25,hDiffXsecErr.GetMaximum()))
        #zaxisTitle = "uncertainty on d#sigma / d#etadp_{T} [pb/GeV]::%.3f,%.3f" % (zmin,zmax)
        drawCorrelationPlot(hDiffXsecErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsecErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        #zaxisTitle = "rel. uncertainty on d#sigma / d#etadp_{T}::%.3f,%.3f" % (0.9*hDiffXsecRelErr.GetMinimum(),hDiffXsecRelErr.GetMaximum())
        if options.fitData:
            zaxisTitle = "rel. uncertainty on d#sigma / d#etadp_{T}::0.010,0.2"
        else:
            zaxisTitle = "rel. uncertainty on d#sigma / d#etadp_{T}::0.025,0.1"
        drawCorrelationPlot(hDiffXsecRelErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsecRelErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        if charge == "plus": zmin,zmax = 0.008,0.028
        else:                zmin,zmax = 0.008,0.029
        #zaxisTitle = "d#sigma / d#etadp_{T} / #sigma_{tot}::%.3f,%.3f" % (0.9*hDiffXsecNorm.GetMinimum(),hDiffXsecNorm.GetMaximum())
        zaxisTitle = "d#sigma / d#etadp_{T} / #sigma_{tot}::%.3f,%.3f" % (zmin,zmax)
        drawCorrelationPlot(hDiffXsecNorm,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsecNorm.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        if charge == "plus": zmin,zmax = 0.0,0.0015
        else:                zmin,zmax = 0.0,0.0015
        #zaxisTitle = "uncertainty on d#sigma / d#etadp_{T} / #sigma_{tot}::%.3f,%.3f" % (0.9*hDiffXsecNormErr.GetMinimum(),hDiffXsecNormErr.GetMaximum())
        zaxisTitle = "uncertainty on d#sigma / d#etadp_{T} / #sigma_{tot}::%.3f,%.3f" % (zmin,zmax)
        drawCorrelationPlot(hDiffXsecNormErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsecNormErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)

        zaxisTitle = "rel. uncertainty on d#sigma / d#etadp_{T} / #sigma_{tot}::%.3f,%.3f" % (0.9*hDiffXsecNormRelErr.GetMinimum(),min(0.1,hDiffXsecNormRelErr.GetBinContent(hDiffXsecNormRelErr.GetMaximumBin())))
        #zaxisTitle = "rel. uncertainty on d#sigma / d#etadp_{T} / #sigma_{tot}::0,0.1"
        drawCorrelationPlot(hDiffXsecNormRelErr,
                            xaxisTitle, yaxisTitle, zaxisTitle,
                            hDiffXsecNormRelErr.GetName(),
                            "ForceTitle",outname,1,1,False,False,False,1, canvasSize="700,625",leftMargin=0.14,rightMargin=0.22,passCanvas=canvas)



######
        # now drawing a TH1 unrolling TH2
        canvUnroll = ROOT.TCanvas("canvUnroll","",3000,2000)

        ratioYaxis = "Rel.Unc.::0.9,1.1"
        if channel == "el": ratioYaxis = "Rel.Unc.::0.8,1.2"

        unrollAlongEta = False
        xaxisTitle = "template global bin"
        if unrollAlongEta:
            xaxisTitle = xaxisTitle + " = 1 + ieta + ipt * %d; ipt in [%d,%d], ieta in [%d,%d]" % (netabins-1,0,nptbins-1,0,netabins-1)
        else:
            xaxisTitle = xaxisTitle + " = 1 + ipt + ieta * %d; ipt in [%d,%d], ieta in [%d,%d]" % (nptbins-1,0,nptbins-1,0,netabins-1)
        h1D_pmaskedexp = getTH1fromTH2(hDiffXsec, hDiffXsecErr, unrollAlongX=unrollAlongEta)        
        drawSingleTH1(h1D_pmaskedexp,xaxisTitle,"d#sigma/d#etadp_{T} [pb/GeV]",
                      "unrolledXsec_abs_{ch}_{fl}".format(ch= charge,fl=channel),
                      outname,labelRatioTmp=ratioYaxis,draw_both0_noLog1_onlyLog2=1,passCanvas=canvUnroll)

        h1D_pmaskedexp_norm = getTH1fromTH2(hDiffXsecNorm, hDiffXsecNormErr, unrollAlongX=unrollAlongEta)        
        drawSingleTH1(h1D_pmaskedexp_norm,xaxisTitle,"d#sigma/d#etadp_{T} / #sigma_{tot} [1/GeV]",
                      "unrolledXsec_norm_{ch}_{fl}".format(ch= charge,fl=channel),
                      outname,labelRatioTmp=ratioYaxis,draw_both0_noLog1_onlyLog2=1,passCanvas=canvUnroll)


# for data, add plot with ratio with expected
        if options.fitData:
            if options.exptoyfile:
                
                getExpFromGen = False
                if options.exptoyfile == "SAME":
                    treeexp = tree
                    getExpFromGen = True
                else:
                    fexp = ROOT.TFile(options.exptoyfile, 'read')
                    treeexp = fexp.Get('fitresults')

        
                hDiffXsec_exp = ROOT.TH2F("hDiffXsec_{lep}_{ch}_exp".format(lep=lepton,ch=charge),
                                          "cross section: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                          genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
                #hDiffXsecErr = ROOT.TH2F("hDiffXsecErr_{lep}_{ch}".format(lep=lepton,ch=charge),
                #                         "cross section uncertainty: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                #                         genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
                hDiffXsecNorm_exp = ROOT.TH2F("hDiffXsecNorm_{lep}_{ch}_exp".format(lep=lepton,ch=charge),
                                              "normalized cross section: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                                              genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))
                #hDiffXsecNormErr = ROOT.TH2F("hDiffXsecNormErr_{lep}_{ch}".format(lep=lepton,ch=charge),
                #                             "normalized cross section uncertainty: {Wch}".format(Wch=Wchannel.replace('W','W{chs}'.format(chs=chargeSign))),
                #                             genBins.Neta, array('d',genBins.etaBins), genBins.Npt, array('d',genBins.ptBins))

                binCount = 0
                print ""
                print "Now reading Hessian to make ratio of data with expected"
                for ieta in range(1,genBins.Neta+1):
                    for ipt in range(1,genBins.Npt+1):

                        #print "\rBin {num}/{tot}".format(num=binCount,tot=nbins),
                        sys.stdout.write('Bin {num}/{tot}   \r'.format(num=binCount,tot=nbins))
                        sys.stdout.flush()
                        binCount += 1

                        # normalized cross section
                        central = utilities.getNormalizedDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                                 nHistBins=2000, minHist=0., maxHist=200., tree=treeexp, getGen=getExpFromGen)         
                        error = utilities.getNormalizedDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                               nHistBins=2000, minHist=0., maxHist=200., tree=treeexp, getErr=True)                    

                        hDiffXsecNorm_exp.SetBinContent(ieta,ipt,central)        
                        hDiffXsecNorm_exp.SetBinError(ieta,ipt,error)         

                        # unnormalized cross section
                        central = utilities.getDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                       nHistBins=2000, minHist=0., maxHist=200., tree=treeexp, getGen=getExpFromGen)                    
                        error = utilities.getDiffXsecFromHessianFast(channel,charge,ieta-1,ipt-1,genBins.Neta,genBins.Npt,ngroup,
                                                                     nHistBins=2000, minHist=0., maxHist=200., tree=treeexp, getErr=True)                    
                        hDiffXsec_exp.SetBinContent(ieta,ipt,central)        
                        hDiffXsec_exp.SetBinError(ieta,ipt,error)         

                if options.normWidth:
                    hDiffXsec_exp.Scale(1.,"width")
                    hDiffXsecNorm_exp.Scale(1.,"width")

                if options.lumiNorm > 0:
                    scaleFactor = 1./options.lumiNorm
                    hDiffXsec_exp.Scale(scaleFactor)

                # now drawing a TH1 unrolling TH2
                unrollAlongEta = False
                xaxisTitle = "template global bin"
                if unrollAlongEta:
                    xaxisTitle = xaxisTitle + " = 1 + ieta + ipt * %d; ipt in [%d,%d], ieta in [%d,%d]" % (netabins-1,0,nptbins-1,0,netabins-1)
                else:
                    xaxisTitle = xaxisTitle + " = 1 + ipt + ieta * %d; ipt in [%d,%d], ieta in [%d,%d]" % (nptbins-1,0,nptbins-1,0,netabins-1)

                h1D_pmaskedexp_exp = getTH1fromTH2(hDiffXsec_exp, h2Derr=None, unrollAlongX=unrollAlongEta)        
                drawDataAndMC(h1D_pmaskedexp, h1D_pmaskedexp_exp,xaxisTitle,"d#sigma/d#etadp_{T} [pb/GeV]",
                              "unrolledXsec_abs_{ch}_{fl}_dataAndExp".format(ch= charge,fl=channel),
                              outname,labelRatioTmp="Data/pred.::0.8,1.2",draw_both0_noLog1_onlyLog2=1,passCanvas=canvUnroll)

                h1D_pmaskedexp_norm_exp = getTH1fromTH2(hDiffXsecNorm_exp, h2Derr=None, unrollAlongX=unrollAlongEta)        
                drawDataAndMC(h1D_pmaskedexp_norm, h1D_pmaskedexp_norm_exp,xaxisTitle,"d#sigma/d#etadp_{T} / #sigma_{tot} [1/GeV]",
                              "unrolledXsec_norm_{ch}_{fl}_dataAndExp".format(ch= charge,fl=channel),
                              outname,labelRatioTmp="Data/pred.::0.8,1.2",draw_both0_noLog1_onlyLog2=1,passCanvas=canvUnroll)


                
                if options.exptoyfile != "SAME": fexp.Close()

        print ""
