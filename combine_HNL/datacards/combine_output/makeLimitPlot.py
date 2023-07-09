import os
import ROOT
import ROOT.TObject
import array

def get_interpolated_coordinates(hist, z):
    # Perform interpolation
    x = ROOT.Double(0)
    y = ROOT.Double(0)
    hist.Interpolate(z, x, y)
    return x, y

if __name__ == "__main__":
    ROOT.gROOT.SetBatch(True)
    masses = [1,2,3,4,5,6,7,8,10,12,14,16,18,20]
    ctaus = ["0.00001", "0.00010", "0.00100", "0.01000", "0.10000", "1", "10", "100", "1000", "10000"];
    binsY = [0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10, 100, 1000, 10000, 100000];
    binsX = [0,1,2,3,4,5,6,7,8,10,12,14,16,18,20,22]

# Create the 2D histogram with variable bins
    hist = ROOT.TH2D("hist", "", len(binsX)-1, array.array('d', binsX), len(binsY)-1, array.array('d', binsY))
#    hist = ROOT.TH2F("hist", "Variable Bin 2D Histogram", len(binsX)-1, binsX, len(binsY)-1, binsY)
#    hist = ROOT.TH2D("hist", "2D Histogram", 20, 0, 20, , 0, 150) 
    for mass in masses:
      for ctau in ctaus:      
         version = "v8"
         filename = "/higgsCombinemHNL_%i_ctau-%s.AsymptoticLimits.mH120.root"%(mass, ctau)
         if os.path.exists(version + filename):
             file = ROOT.TFile(version + filename, "READ")
             tree = file.Get("limit")
             qlimit = tree.GetLeaf("limit")
             i=0
             for event in tree:
#             print (event)
                 i=i+1
                 value = qlimit.GetValue()
                 rounded_limit = round(value, 2)
######################################################## Need to check ####
                 if tree.GetEntries() == 6 and i==3:
                     hist.Fill(mass, float(ctau), rounded_limit)
                 if tree.GetEntries() == 12 and i==9:
                     hist.Fill(mass, float(ctau), rounded_limit)                   
                     print (mass, ctau, rounded_limit)
#######################################################
    # Do something with the leaf value
    #             print(rounded_limit, i)         
#    ROOT.gStyle.SetPalette(ROOT.kRainBow)
#             target_z = 1.0 
#             interpolated_x, interpolated_y = get_interpolated_coordinates(hist, target_z)
    tex1 = ROOT.TLatex(0.1, 0.95, "#bf{CMS} #it{Work in Progress}");
    tex1.SetNDC();
    tex1.SetTextAlign(13);
    tex1.SetTextFont(42);
    tex1.SetTextSize(0.04);
    tex1.SetLineWidth(2);


    hist.SetStats(0)
    canvas = ROOT.TCanvas("canvas", "canvas", 800, 600)
    canvas.cd()
    hist.GetXaxis().SetTitle("Mass (GeV)")
    hist.GetYaxis().SetTitle("c#tau (mm)")
    canvas.SetLogy()
    hist.SetMarkerColor(2)
    hist.Draw("COLZ TEXT")
    tex1.Draw("SAME")
    canvas.RedrawAxis()
    canvas.SaveAs("/eos/user/p/prsaha/www/vlq_review/combined_limit_HNL_"+ version +".png")
    canvas.SaveAs("/eos/user/p/prsaha/www/vlq_review/combined_limit_HNL_"+ version +".pdf")

