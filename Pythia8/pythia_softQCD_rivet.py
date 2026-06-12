import FWCore.ParameterSet.Config as cms
from Configuration.Generator.Pythia8CommonSettings_cfi import *
from Configuration.Generator.Pythia8CUEP8M1Settings_cfi import *
from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing('analysis')
options.register('iSeed',
                 42,
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.int,
                 'Random seed')
options.register('outputBase',
                 'softQCD_seed42',
                 VarParsing.multiplicity.singleton,
                 VarParsing.varType.string,
                 'Output file base name without extension')
options.parseArguments()

process = cms.Process('GEN')

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

process.maxEvents = cms.untracked.PSet(
    input=cms.untracked.int32(options.maxEvents if options.maxEvents > 0 else 1000)
)

process.source = cms.Source('EmptySource')
process.options = cms.untracked.PSet()
process.genstepfilter.triggerConditions = cms.vstring('generation_step')

process.generator = cms.EDFilter(
    'Pythia8GeneratorFilter',
    pythiaPylistVerbosity=cms.untracked.int32(0),
    maxEventsToPrint=cms.untracked.int32(0),
    pythiaHepMCVerbosity=cms.untracked.bool(False),
    filterEfficiency=cms.untracked.double(1.0),
    comEnergy=cms.double(13600.0),
    PythiaParameters=cms.PSet(
        pythia8CommonSettingsBlock,
        pythia8CUEP8M1SettingsBlock,
        processParameters=cms.vstring(
            'Print:quiet = on',
            'Next:numberShowInfo = 0',
            'Next:numberShowProcess = 0',
            'Next:numberShowEvent = 0',
            'HardQCD:all = off',
            'SoftQCD:all = on',
        ),
        parameterSets=cms.vstring(
            'pythia8CommonSettings',
            'pythia8CUEP8M1Settings',
            'processParameters',
        ),
    ),
)

process.generation_step = cms.Path(process.pgen)
process.genfiltersummary_step = cms.EndPath(process.genFilterSummary)
process.endjob_step = cms.EndPath(process.endOfProcess)
process.schedule = cms.Schedule(
    process.generation_step,
    process.genfiltersummary_step,
    process.endjob_step,
)

for path in process.paths:
    getattr(process, path)._seq = process.generator * getattr(process, path)._seq

process.rivetAnalyzer.AnalysisNames = cms.vstring('allParticles')
process.rivetAnalyzer.OutputFile = cms.string(options.outputBase + '.yoda')
process.generation_step += process.rivetAnalyzer

process.source.firstRun = cms.untracked.uint32(1)
process.RandomNumberGeneratorService.generator.initialSeed = options.iSeed
process.MessageLogger.cerr.FwkReport.reportEvery = 100
