import FWCore.ParameterSet.Config as cms
from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.Pythia8CUEP8M1Settings_cfi import *
from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing ('analysis')
options.register ('pTHatMax',
              -1,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.int,
              "Maximum pTHat")
options.register ('pTHatMin',
              137,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.int,
              "Minimum pTHat")
options.register ('iSeed',
              42,
              VarParsing.multiplicity.singleton,
              VarParsing.varType.int,
              "Random seed")
options.parseArguments()

process = cms.Process('GEN')

# import of standard configurations
process.load('Configuration.StandardSequences.Services_cff')
process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.EventContent.EventContent_cff')
process.load('SimGeneral.MixingModule.mixNoPU_cfi')
process.load('Configuration.StandardSequences.Generator_cff')
process.load('IOMC.EventVertexGenerators.VtxSmearedRealistic8TeVCollision_cfi')
process.load('GeneratorInterface.Core.genFilterSummary_cff')
process.load('GeneratorInterface.RivetInterface.rivetAnalyzer_cfi')
process.load('Configuration.StandardSequences.EndOfProcess_cff')

import sys

# ===============================================================
# Use a small sample while debugging. Restore 10000 for production.
# ===============================================================
process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(10)
)

process.source = cms.Source("EmptySource")
process.options = cms.untracked.PSet(
)

process.genstepfilter.triggerConditions=cms.vstring("generation_step")

process.generator = cms.EDFilter("Pythia8GeneratorFilter",
                         # ===============================================================
                         # Verbosity for debugging.
                         # pythiaPylistVerbosity = 1 prints the particle list
                         # (id, status, mothers, daughters, energy) so the status
                         # and mother of the ~1 TeV nucleons can be inspected.
                         # maxEventsToPrint controls how many events are dumped.
                         # ===============================================================
                         pythiaPylistVerbosity = cms.untracked.int32(1),
                         maxEventsToPrint = cms.untracked.int32(3),
                         # ===============================================================
                         # Set to True to also dump the HepMC record if needed.
                         # ===============================================================
                         pythiaHepMCVerbosity = cms.untracked.bool(False),
                         filterEfficiency = cms.untracked.double(1.0),
                         comEnergy = cms.double(13600.0),
                         PythiaParameters = cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CUEP8M1SettingsBlock,
        processParameters = cms.vstring(
            'SoftQCD:all = on',
            # ===============================================================
            # These pTHat cuts have NO effect on SoftQCD. They are kept here
            # only so the value shows up in the log for the diff test.
            # ===============================================================
            'PhaseSpace:pTHatMin = %i'%options.pTHatMin,
            'PhaseSpace:pTHatMax = %i'%options.pTHatMax,
            ),
        parameterSets = cms.vstring('pythia8CommonSettings',
                                    'pythia8CUEP8M1Settings',
                                    'processParameters',
                                    )
        )
                         )

process.generation_step = cms.Path(process.pgen)
process.genfiltersummary_step = cms.EndPath(process.genFilterSummary)
process.endjob_step = cms.EndPath(process.endOfProcess)
process.schedule = cms.Schedule(process.generation_step,process.genfiltersummary_step,process.endjob_step)

# ===============================================================
# Prepend the generator to every path so it always runs first.
# ===============================================================
for path in process.paths:
    getattr(process,path)._seq = process.generator * getattr(process,path)._seq

process.rivetAnalyzer.AnalysisNames = cms.vstring('allParticles')
process.rivetAnalyzer.OutputFile = cms.string('allParticles.yoda')
process.generation_step += process.rivetAnalyzer

process.source.firstRun = cms.untracked.uint32(1)
process.RandomNumberGeneratorService.generator.initialSeed = options.iSeed
process.MessageLogger.cerr.FwkReport.reportEvery = 50000
