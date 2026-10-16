// Project-local Chordino comparison host. Accepts RIFF PCM16 mono WAV only.
// Uses Vamp's documented input-domain and buffering adapters; no audio downloads.
#include <vamp-hostsdk/PluginLoader.h>
#include <vamp-hostsdk/PluginInputDomainAdapter.h>
#include <algorithm>
#include <cstdint>
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
        if (!feature.hasTimestamp || feature.label.find_first_of("\t\r\n") != std::string::npos)
            throw std::runtime_error("invalid native chord feature");
        double seconds = feature.timestamp.sec + feature.timestamp.nsec/1e9;
        std::cout << std::fixed << std::setprecision(9) << seconds << '\t' << feature.label << '\n';
    }
}
int main(int argc, char **argv) {
    try {
        if (argc != 2) throw std::runtime_error("usage: chordino-host PCM16-mono.wav");
        Audio audio = loadWav(argv[1]);
        auto *loader = Vamp::HostExt::PluginLoader::getInstance();
        auto *plugin = loader->loadPlugin("nnls-chroma:chordino", float(audio.rate), 0);
        if (!plugin) throw std::runtime_error("Chordino plugin unavailable; set project-local VAMP_PATH");
        const int version = plugin->getPluginVersion();
        const size_t preferredHop = plugin->getPreferredStepSize();
        const size_t preferredBlock = plugin->getPreferredBlockSize();
        std::unique_ptr<Vamp::HostExt::PluginInputDomainAdapter> adapter(
            new Vamp::HostExt::PluginInputDomainAdapter(plugin));
        adapter->setProcessTimestampMethod(Vamp::HostExt::PluginInputDomainAdapter::ShiftData);
        const size_t actualHop = preferredHop, actualBlock = preferredBlock;
        const size_t hostBlock = actualBlock;
        if (!actualHop || !actualBlock || !adapter->initialise(1, actualHop, actualBlock))
            throw std::runtime_error("Chordino adapter initialise failed");
        const auto outputs = adapter->getOutputDescriptors();
        int chordOutput = -1;
        for (size_t i = 0; i < outputs.size(); ++i)
            if (outputs[i].identifier == "simplechord") chordOutput = int(i);
        if (chordOutput < 0) throw std::runtime_error("simplechord output missing");
        std::cout << "# {\"plugin_version\":" << version << ",\"sample_rate_hz\":" << audio.rate
            << ",\"frames\":" << audio.samples.size()
            << ",\"preferred_hop\":" << preferredHop << ",\"preferred_block\":" << preferredBlock
            << ",\"hop_size\":" << actualHop << ",\"block_size\":" << actualBlock
            << ",\"host_block\":" << hostBlock << ",\"timestamp_method\":\"ShiftData\",\"window\":\"Hann\",\"final_N_is_termination_marker\":true,\"parameters\":{";
        const auto parameters = adapter->getParameterDescriptors();
        for (size_t i = 0; i < parameters.size(); ++i) {
            if (i) std::cout << ',';
            std::cout << '"' << parameters[i].identifier << "\":"
                << adapter->getParameter(parameters[i].identifier);
        }
        std::cout << "}}\n";
        std::vector<float> block(hostBlock);
        // Sliding input blocks provide the plugin's preferred hop without a
        // buffering wrapper. ShiftData centers the spectrum at `frame`, pads
        // the initial half-window, and avoids losing the recording's final
        // half-window to a streaming wrapper's limited tail flush.
        for (size_t frame = 0; frame < audio.samples.size(); frame += actualHop) {
            std::fill(block.begin(), block.end(), 0.0f);
            const size_t count = std::min(hostBlock, audio.samples.size()-frame);
            std::copy_n(audio.samples.begin()+frame, count, block.begin());
            const float *buffer = block.data();
            emit(adapter->process(&buffer, Vamp::RealTime::frame2RealTime(frame, audio.rate)), chordOutput);
        }
        emit(adapter->getRemainingFeatures(), chordOutput);
        return 0;
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
