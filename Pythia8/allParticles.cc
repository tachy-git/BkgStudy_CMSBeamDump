#include "Rivet/Analysis.hh"
#include "Rivet/Projections/FinalState.hh"
#include "Rivet/Projections/FastJets.hh"

#include "TFile.h"
#include "TH2D.h"

#include <cmath>
#include <map>
#include <string>
#include <vector>

namespace Rivet {

  class allParticles : public Analysis {
  public:
    allParticles()
      : Analysis("allParticles")
    { }

    void init() override {
      declare(FastJets(FinalState(), FastJets::ANTIKT, 0.4), "jets");
      rootOut = new TFile("allParticles.root", "RECREATE");

      std::vector<double> eAxis;
      for (double i = 1.0e-3; i < 5.0e3; i *= std::pow(10.0, 0.1)) {
        eAxis.push_back(i);
      }

      std::vector<double> thetaAxis;
      for (double i = 0.0; i < 181.0; i += 1.0) {
        thetaAxis.push_back(i);
      }

      const int nx = eAxis.size() - 1;
      const int ny = thetaAxis.size() - 1;

      bookParticle(22, "photon", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(12, "nue", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-12, "nueb", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(14, "numu", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-14, "numub", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(16, "nutau", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-16, "nutaub", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(111, "pi0", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(211, "pip", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-211, "pim", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(221, "eta", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(321, "kp", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-321, "km", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(2212, "p", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-2212, "pb", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(2112, "n", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-2112, "nb", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(11, "e", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-11, "ep", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(-13, "mup", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(13, "mum", nx, eAxis.data(), ny, thetaAxis.data());
      bookParticle(2114, "lambda", nx, eAxis.data(), ny, thetaAxis.data());
    }

    void analyze(const Event& event) override {
      const Jets jets = apply<FastJets>(event, "jets").jetsByPt(Cuts::pT > 30.0*GeV);
      for (const Jet& jet : jets) {
        if (jet.absrapidity() > 3.0) continue;
        for (const Particle& particle : jet.constituents()) {
          const auto hist = hparticle.find(particle.pid());
          if (hist == hparticle.end()) {
            continue;
          }

          const FourMomentum& momentum = particle.momentum();
          for (const auto& selection : hist->second) {
            if (jet.pT() > selection.first * GeV)
              selection.second->Fill(particle.E()/GeV, momentum.theta() * 180.0 / M_PI);
          }
        }
      }
    }

    void finalize() override {
      for (const auto& particleHist : hparticle) {
        for (const auto& selection : particleHist.second) {
          rootOut->GetDirectory(("jetpt" + std::to_string(selection.first)).c_str())->cd();
          selection.second->Write();
          delete selection.second;
        }
      }
      hparticle.clear();

      rootOut->Write();
      rootOut->Close();
      delete rootOut;
      rootOut = nullptr;
    }

  private:
    void bookParticle(int pid, const std::string& name, int nx, const double* xbins, int ny, const double* ybins) {
      for (int cut : {30, 50, 100}) {
        const std::string directory = "jetpt" + std::to_string(cut);
        if (!rootOut->GetDirectory(directory.c_str())) rootOut->mkdir(directory.c_str());
        rootOut->GetDirectory(directory.c_str())->cd();
        auto* hist = new TH2D(name.c_str(), name.c_str(), nx, xbins, ny, ybins);
        hist->SetDirectory(nullptr);
        hparticle[pid][cut] = hist;
      }
    }

    TFile* rootOut = nullptr;
    std::map<int, std::map<int, TH2D*>> hparticle;
  };

  DECLARE_RIVET_PLUGIN(allParticles);

}
