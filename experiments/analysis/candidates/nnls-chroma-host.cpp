// Project-local NNLS-Chroma acoustic evidence host. RIFF PCM16 mono only.
// Uses the existing reviewed plugin, never Chordino labels or timing references.
#include <vamp-hostsdk/PluginLoader.h>
#include <vamp-hostsdk/PluginInputDomainAdapter.h>
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

static uint16_t u16(const unsigned char *p) {
    return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}
static uint32_t u32(const unsigned char *p) {
    return uint32_t(p[0]) | (uint32_t(p[1]) << 8) |
        (uint32_t(p[2]) << 16) | (uint32_t(p[3]) << 24);
}
struct Audio { uint32_t rate; std::vector<float> samples; };
static Audio loadWav(const std::string &path) {
    std::ifstream stream(path, std::ios::binary | std::ios::ate);
    if (!stream) throw std::runtime_error("cannot open WAV");
    auto length = stream.tellg();
    if (length < 12 || length > 512 * 1024 * 1024)
        throw std::runtime_error("invalid or oversized WAV (512 MiB limit)");
    std::vector<unsigned char> bytes(static_cast<size_t>(length));
    stream.seekg(0); stream.read(reinterpret_cast<char*>(bytes.data()), length);
    if (!stream || std::string(bytes.begin(), bytes.begin()+4) != "RIFF" ||
        std::string(bytes.begin()+8, bytes.begin()+12) != "WAVE")
        throw std::runtime_error("requires RIFF WAV");
    uint32_t rate = 0; size_t dataStart = 0, dataSize = 0;
    bool validFormat = false;
    for (size_t offset = 12; offset + 8 <= bytes.size();) {
        const std::string tag(bytes.begin()+offset, bytes.begin()+offset+4);
        const size_t size = u32(bytes.data()+offset+4), start = offset+8;
        if (size > bytes.size()-start) throw std::runtime_error("truncated WAV chunk");
        if (tag == "fmt ") {
            if (size < 16 || u16(bytes.data()+start) != 1 ||
                u16(bytes.data()+start+2) != 1 || u16(bytes.data()+start+14) != 16 ||
                u16(bytes.data()+start+12) != 2)
                throw std::runtime_error("requires PCM16 mono WAV");
            rate = u32(bytes.data()+start+4);
            if (rate < 8000 || rate > 192000) throw std::runtime_error("invalid sample rate");
            validFormat = true;
        } else if (tag == "data") { dataStart = start; dataSize = size; }
        offset = start + size + (size & 1);
    }
    if (!validFormat || !dataSize || dataSize % 2)
        throw std::runtime_error("missing format or nonempty PCM16 data");
    Audio audio{rate, std::vector<float>(dataSize/2)};
    for (size_t i = 0; i < audio.samples.size(); ++i) {
        uint16_t value = u16(bytes.data()+dataStart+2*i);
        int signedValue = value < 32768 ? value : int(value)-65536;
        audio.samples[i] = float(signedValue)/32768.0f;
    }
    return audio;
}
static void emit(const Vamp::Plugin::FeatureSet &features, int output) {
    auto found = features.find(output);
    if (found == features.end()) return;
    for (const auto &feature : found->second) {
        if (!feature.hasTimestamp || feature.values.size() != 12)
            throw std::runtime_error("expected 12-bin timestamped chroma feature");
        double seconds = feature.timestamp.sec + feature.timestamp.nsec/1e9;
        if (!std::isfinite(seconds)) throw std::runtime_error("nonfinite feature timestamp");
        std::cout << std::fixed << std::setprecision(9) << seconds;
        for (float value : feature.values) {
            if (!std::isfinite(value) || value < 0)
                throw std::runtime_error("invalid chroma activation");
            std::cout << '\t' << std::scientific << std::setprecision(9) << value;
        }
        std::cout << '\n';
    }
}
int main(int argc, char **argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: nnls-chroma-host PCM16-mono.wav");
        Audio audio = loadWav(argv[1]);
        auto *loader = Vamp::HostExt::PluginLoader::getInstance();
        auto *plugin = loader->loadPlugin("nnls-chroma:nnls-chroma", float(audio.rate), 0);
        if (!plugin) throw std::runtime_error("NNLS-Chroma unavailable; set project-local VAMP_PATH");
        const int version = plugin->getPluginVersion();
        const size_t hop = plugin->getPreferredStepSize();
        const size_t blockSize = plugin->getPreferredBlockSize();
        std::unique_ptr<Vamp::HostExt::PluginInputDomainAdapter> adapter(
            new Vamp::HostExt::PluginInputDomainAdapter(plugin));
        adapter->setProcessTimestampMethod(Vamp::HostExt::PluginInputDomainAdapter::ShiftData);
        if (!hop || !blockSize || !adapter->initialise(1, hop, blockSize))
            throw std::runtime_error("NNLS-Chroma initialise failed");
        const auto outputs = adapter->getOutputDescriptors();
        int output = -1;
        for (size_t i = 0; i < outputs.size(); ++i)
            if (outputs[i].identifier == "chroma") output = int(i);
        if (output < 0 || outputs[output].binCount != 12 || outputs[output].binNames.size() != 12)
            throw std::runtime_error("12-bin chroma output missing");
        const auto adjustment = adapter->getTimestampAdjustment();
        if (adjustment.sec != 0 || adjustment.nsec != 0)
            throw std::runtime_error("ShiftData must have zero timestamp adjustment");
        std::cout << "# {\"plugin\":\"nnls-chroma:nnls-chroma\",\"output\":\"chroma\",\"plugin_version\":"
            << version << ",\"sample_rate_hz\":" << audio.rate << ",\"frames\":" << audio.samples.size()
            << ",\"hop_size\":" << hop << ",\"block_size\":" << blockSize
            << ",\"timestamp_method\":\"ShiftData\",\"timestamp_adjustment_seconds\":0"
            << ",\"window\":\"Hann\",\"timestamp_semantics\":\"analysis window center\",\"native_bin_names\":[";
        for (size_t i = 0; i < 12; ++i) {
            if (i) std::cout << ',';
            std::cout << '\"' << outputs[output].binNames[i] << '\"';
        }
        std::cout << "],\"parameters\":{";
        const auto parameters = adapter->getParameterDescriptors();
        for (size_t i = 0; i < parameters.size(); ++i) {
            if (i) std::cout << ',';
            std::cout << '\"' << parameters[i].identifier << "\":"
                << adapter->getParameter(parameters[i].identifier);
        }
        std::cout << "}}\n";
        std::vector<float> block(blockSize);
        // ShiftData retains preceding half-window samples. Each frame is
        // centered on `frame`; initial/final regions are zero padded.
        for (size_t frame = 0; frame < audio.samples.size(); frame += hop) {
            std::fill(block.begin(), block.end(), 0.0f);
            const size_t count = std::min(blockSize, audio.samples.size()-frame);
            std::copy_n(audio.samples.begin()+frame, count, block.begin());
            const float *buffer = block.data();
            emit(adapter->process(&buffer, Vamp::RealTime::frame2RealTime(frame, audio.rate)), output);
        }
        // NNLS-Chroma computes tuning and note activations here. These are
        // independent acoustic vectors, not a duration expansion of labels.
        emit(adapter->getRemainingFeatures(), output);
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
