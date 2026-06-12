#include "Rivet/Analysis.hh"

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
    }

    void analyze(const Event& event) override {
      for (const Particle& particle : event.allParticles()) {
        const auto hist = hparticle.find(particle.pid());
        if (hist == hparticle.end()) {
          continue;
        }

        const FourMomentum& momentum = particle.momentum();
        hist->second->Fill(particle.E(), momentum.theta() * 180.0 / M_PI);
      }
    }

    void finalize() override {
      rootOut->cd();
      for (const auto& particleHist : hparticle) {
        particleHist.second->Write();
        delete particleHist.second;
      }
      hparticle.clear();

      rootOut->Write();
      rootOut->Close();
      delete rootOut;
      rootOut = nullptr;
    }

  private:
    void bookParticle(int pid, const std::string& name, int nx, const double* xbins, int ny, const double* ybins) {
      hparticle[pid] = new TH2D(name.c_str(), name.c_str(), nx, xbins, ny, ybins);
    }

    TFile* rootOut = nullptr;
    std::map<int, TH2D*> hparticle;
  };

  DECLARE_RIVET_PLUGIN(allParticles);

}
