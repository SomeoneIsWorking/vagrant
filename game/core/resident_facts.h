#pragma once

#include <cstdint>

namespace vagrant::resident {

// RE-19: exact resident/TITLE bootstrap facts measured from the SHA-bound SLUS_010.40 by
// tools/re_resident.py. These are finite guest leaves; neither VSync call is dispatched.
inline constexpr std::uint32_t kCxxMain = 0x8001F5ECu;
inline constexpr std::uint32_t kSetVideoMode = 0x80020354u;
inline constexpr std::uint32_t kSetDispMask = 0x800285B8u;
inline constexpr std::uint32_t kResetCallback = 0x8001F8D4u;
inline constexpr std::uint32_t kResetGraph = 0x800282D4u;
inline constexpr std::uint32_t kSetGraphDebug = 0x80028448u;

inline constexpr std::uint32_t kCardStop = 0x80026A04u;
inline constexpr std::uint32_t kCardStart = 0x80026974u;
inline constexpr std::uint32_t kCardProbe = 0x8002EA40u;
inline constexpr std::uint32_t kCardConfigure = 0x8002EE84u;
inline constexpr std::uint32_t kCardConfigureEvents = 0x8002F094u;
inline constexpr std::uint32_t kCardConfigureHardware = 0x8002EF90u;
inline constexpr std::uint32_t kCardConfigureSoftware = 0x8002F024u;
inline constexpr std::uint32_t kCardConfigureFilesystem = 0x8002EEB4u;
inline constexpr std::uint32_t kCardResume = 0x80026984u;
inline constexpr std::uint32_t kCardStartCom = 0x8002EE94u;

inline constexpr std::uint32_t kBuInit = 0x80026884u;
inline constexpr std::uint32_t kPadInitDirect = 0x8002DCC4u;
inline constexpr std::uint32_t kPadResetDefaults = 0x80043034u;
inline constexpr std::uint32_t kPadStartCom = 0x8002B804u;
inline constexpr std::uint32_t kUnlockPadModeSwitch = 0x80042FF0u;
inline constexpr std::uint32_t kResetPadAct = 0x80043668u;
inline constexpr std::uint32_t kReverbOff = 0x8001E5C4u;
inline constexpr std::uint32_t kDsInit = 0x800238C4u;
inline constexpr std::uint32_t kInitRand = 0x8004274Cu;
inline constexpr std::uint32_t kResetEnabled = 0x80055C88u;
inline constexpr std::uint32_t kSaveGameClearData = 0x8005E214u;
inline constexpr std::uint32_t kPadBuffer0 = 0x8005DFF0u;
inline constexpr std::uint32_t kPadBuffer1 = 0x8005E012u;

inline constexpr std::uint32_t kOverlayGetSp = 0x80010AA4u;
inline constexpr std::uint32_t kTitleOuterStack = 0x80050474u;
inline constexpr std::uint32_t kTitlePrgLba = 0x0003E800u;
inline constexpr std::uint32_t kTitlePrgSize = 0x00087800u;
inline constexpr std::uint32_t kTitleOverlayBase = 0x80068800u;
inline constexpr std::uint32_t kTitleEntry = 0x80071334u;
inline constexpr std::uint32_t kTitleStartState = 0x80050470u;

inline constexpr std::uint32_t kClearImage = 0x800287D4u;
inline constexpr std::uint32_t kDrawSync = 0x80028650u;
inline constexpr std::uint32_t kInitScreen = 0x80042054u;
inline constexpr std::uint32_t kClearImage2 = 0x80028864u;
inline constexpr std::uint32_t kLoadImage = 0x800288FCu;
inline constexpr std::uint32_t kLoadingImageHeader = 0x80049150u;
inline constexpr std::uint32_t kLoadingImageData = kLoadingImageHeader + 4u;
inline constexpr std::uint32_t kProjectionDistance = 0x8005E248u;

inline constexpr std::uint32_t kReverbOn = 0x8001E5E4u;
inline constexpr std::uint32_t kInitGeom = 0x80011C44u;
inline constexpr std::uint32_t kDrawSyncCallback = 0x80028558u;
inline constexpr std::uint32_t kGpuSyncCallback = 0x8004271Cu;
inline constexpr std::uint32_t kVSyncCallback = 0x8001F964u;
inline constexpr std::uint32_t kVSyncVoidCallback = 0x80042724u;
inline constexpr std::uint32_t kInitHeap = 0x80043F74u;
inline constexpr std::uint32_t kHeapBase = 0x8010C000u;
inline constexpr std::uint32_t kHeapSize = 0x000F2000u;
inline constexpr std::uint32_t kInitCdQueue = 0x80044AE4u;
inline constexpr std::uint32_t kDiskReset = 0x80044A60u;
inline constexpr std::uint32_t kLoadMenuSound = 0x800468FCu;
inline constexpr std::uint32_t kInitSound = 0x80011DACu;
inline constexpr std::uint32_t kSetCdVolume = 0x80013230u;
inline constexpr std::uint32_t kAllocHeapR = 0x80043E3Cu;
inline constexpr std::uint32_t kFreeHeapR = 0x80043C60u;
inline constexpr std::uint32_t kDiskInitRead = 0x80044340u;
inline constexpr std::uint32_t kDiskGetState = 0x80044310u;
inline constexpr std::uint32_t kProcessCdQueue = 0x80044C74u;
inline constexpr std::uint32_t kLoadWaveBank = 0x80012BB8u;
inline constexpr std::uint32_t kLoadProgramBank = 0x800131DCu;
inline constexpr std::uint32_t kBindSfxBlob = 0x80011DECu;

inline constexpr std::uint32_t kWave0000Lba = 0xF618u;
inline constexpr std::uint32_t kWave0000Size = 0x8800u;
inline constexpr std::uint32_t kWave0005Lba = 0xF62Du;
inline constexpr std::uint32_t kWave0005Size = 0x12000u;
inline constexpr std::uint32_t kWave0200Lba = 0x10C65u;
inline constexpr std::uint32_t kWave0200Size = 0x18800u;
inline constexpr std::uint32_t kEffect00Lba = 0x128E0u;
inline constexpr std::uint32_t kEffect00Size = 0x5800u;
inline constexpr std::uint32_t kSfxData = 0x80050478u;

inline constexpr std::uint32_t kSoundControl0 = 0x8005FE70u;
inline constexpr std::uint32_t kSoundControl1 = 0x8005FE74u;
inline constexpr std::uint32_t kSoundControl2 = 0x8005FE78u;
inline constexpr std::uint32_t kSoundControl3 = 0x8005FE7Cu;
inline constexpr std::uint32_t kSoundControl4 = 0x8005FE80u;
inline constexpr std::uint32_t kSoundControl5 = 0x8005FE84u;
inline constexpr std::uint32_t kInGame = 0x8005E240u;
inline constexpr std::uint32_t kButtonHeldFrameCount = 0x80055C90u;
inline constexpr std::uint32_t kGameTime = 0x80061074u;
inline constexpr std::uint32_t kGameTimeTickSpeed = 0x8005E24Cu;
inline constexpr std::uint32_t kMainStateFlag = 0x80060068u;
inline constexpr std::uint32_t kDmaCallbackTable = 0x80032128u;

inline constexpr std::uint32_t kDiskStateIdle = 0u;
inline constexpr std::uint32_t kDiskStateSeekReady = 1u;
inline constexpr std::uint32_t kDiskStateReadReady = 2u;
inline constexpr std::uint32_t kDiskStateReading = 3u;
inline constexpr std::uint32_t kDiskStateReadInit = 5u;

} // namespace vagrant::resident
