/*
 * C wrapper for Indemind SDK - for Python ctypes
 * Uses raw callbacks to avoid cv::Mat ABI issues across shared libraries.
 * Supports: raw image, depth, disparity, rectified, point cloud, IMU, detector, calibration.
 */

#include <opencv2/opencv.hpp>
#include "imrsdk.h"
#include "types.h"
#include <cstring>
#include <mutex>
#include <atomic>
#include <vector>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

// ============================================================
// Global state
// ============================================================
static indem::CIMRSDK* g_sdk = nullptr;
static std::mutex g_mutex;

// --- Raw camera frame ---
static unsigned char* g_frame_buf = nullptr;
static int g_frame_width = 0;
static int g_frame_height = 0;
static int g_frame_channels = 0;
static std::atomic<bool> g_frame_ready{false};
static std::atomic<int> g_callback_count{0};

// --- Depth ---
static std::mutex g_depth_mutex;
static unsigned short* g_depth_buf = nullptr;
static int g_depth_width = 0;
static int g_depth_height = 0;
static std::atomic<bool> g_depth_ready{false};
static bool g_has_depth = false;

// --- Disparity ---
static std::mutex g_disp_mutex;
static float* g_disp_buf = nullptr;
static int g_disp_width = 0;
static int g_disp_height = 0;
static std::atomic<bool> g_disp_ready{false};
static bool g_has_disp = false;

// --- Rectified images ---
static std::mutex g_rect_mutex;
static unsigned char* g_rect_buf = nullptr;   // left+right side-by-side grayscale
static int g_rect_width = 0;                  // total width (left_w * 2)
static int g_rect_height = 0;
static int g_rect_channels = 0;
static std::atomic<bool> g_rect_ready{false};
static bool g_has_rect = false;

// --- Point cloud ---
static std::mutex g_pts_mutex;
static float* g_pts_buf = nullptr;   // XYZ interleaved
static int g_pts_count = 0;         // number of points
static int g_pts_width = 0;
static int g_pts_height = 0;
static std::atomic<bool> g_pts_ready{false};
static bool g_has_pts = false;

// --- IMU ring buffer ---
struct ImuSample {
    double timestamp;
    float accel[3];
    float gyro[3];
};
static std::mutex g_imu_mutex;
static const int IMU_RING_SIZE = 2000;
static ImuSample g_imu_ring[IMU_RING_SIZE];
static int g_imu_head = 0;
static int g_imu_count = 0;
static bool g_has_imu = false;

// --- Detector ---
struct DetBox {
    int x, y, w, h;
    float score;
    int class_id;
};
static std::mutex g_det_mutex;
static DetBox g_det_boxes[256];
static int g_det_box_count = 0;
static unsigned char* g_det_img_buf = nullptr;
static int g_det_img_width = 0;
static int g_det_img_height = 0;
static int g_det_img_channels = 0;
static std::atomic<bool> g_det_ready{false};
static bool g_has_det = false;

// --- Calibration cache (use pointer to avoid static std::map construction ABI issues) ---
static bool g_calib_cached = false;
static indem::MoudleAllParam* g_calib = nullptr;

extern "C" {

// ============================================================
// Init / Release
// ============================================================

EXPORT int imsee_init(int resolution, int fps) {
    if (g_sdk != nullptr) return -1;

    g_sdk = new indem::CIMRSDK();
    indem::MRCONFIG config = {0};
    config.bSlam = false;
    config.imgResolution = (resolution == 2) ? indem::IMG_1280 : indem::IMG_640;
    config.imgFrequency = fps;
    config.imuFrequency = 1000;

    if (!g_sdk->Init(config)) {
        delete g_sdk;
        g_sdk = nullptr;
        return -2;
    }

    // Raw camera callback (left+right side-by-side grayscale)
    g_sdk->RegistModuleCameraCallback(
        [](double time, unsigned char *pLeft, unsigned char *pRight,
           int width, int height, int channel, void *pParam) {

            if (pLeft == nullptr || width <= 0 || height <= 0) return;

            std::lock_guard<std::mutex> lock(g_mutex);

            bool has_right = (pRight != nullptr);
            int out_width = has_right ? width * 2 : width;
            int out_size = out_width * height;

            if (g_frame_buf == nullptr || g_frame_width != out_width || g_frame_height != height) {
                delete[] g_frame_buf;
                g_frame_buf = new unsigned char[out_size];
                g_frame_width = out_width;
                g_frame_height = height;
                g_frame_channels = 1;
            }

            if (channel == 1) {
                for (int y = 0; y < height; y++)
                    memcpy(g_frame_buf + y * out_width, pLeft + y * width, width);
                if (has_right)
                    for (int y = 0; y < height; y++)
                        memcpy(g_frame_buf + y * out_width + width, pRight + y * width, width);
            } else if (channel == 3) {
                for (int y = 0; y < height; y++)
                    for (int x = 0; x < width; x++) {
                        int si = (y * width + x) * 3;
                        int di = y * out_width + x;
                        g_frame_buf[di] = (unsigned char)(
                            0.114f * pLeft[si] + 0.587f * pLeft[si+1] + 0.299f * pLeft[si+2]);
                    }
                if (has_right)
                    for (int y = 0; y < height; y++)
                        for (int x = 0; x < width; x++) {
                            int si = (y * width + x) * 3;
                            int di = y * out_width + width + x;
                            g_frame_buf[di] = (unsigned char)(
                                0.114f * pRight[si] + 0.587f * pRight[si+1] + 0.299f * pRight[si+2]);
                        }
            }

            g_frame_ready.store(true);
            g_callback_count.fetch_add(1);
        },
        nullptr
    );

    return 0;
}

EXPORT void imsee_release() {
    if (g_sdk != nullptr) {
        g_sdk->Release();
        delete g_sdk;
        g_sdk = nullptr;
    }

    {
        std::lock_guard<std::mutex> lock(g_mutex);
        delete[] g_frame_buf; g_frame_buf = nullptr;
        g_frame_width = g_frame_height = g_frame_channels = 0;
        g_frame_ready.store(false);
    }
    {
        std::lock_guard<std::mutex> lock(g_depth_mutex);
        delete[] g_depth_buf; g_depth_buf = nullptr;
        g_depth_width = g_depth_height = 0;
        g_depth_ready.store(false);
    }
    {
        std::lock_guard<std::mutex> lock(g_disp_mutex);
        delete[] g_disp_buf; g_disp_buf = nullptr;
        g_disp_width = g_disp_height = 0;
        g_disp_ready.store(false);
    }
    {
        std::lock_guard<std::mutex> lock(g_rect_mutex);
        delete[] g_rect_buf; g_rect_buf = nullptr;
        g_rect_width = g_rect_height = g_rect_channels = 0;
        g_rect_ready.store(false);
    }
    {
        std::lock_guard<std::mutex> lock(g_pts_mutex);
        delete[] g_pts_buf; g_pts_buf = nullptr;
        g_pts_count = g_pts_width = g_pts_height = 0;
        g_pts_ready.store(false);
    }
    {
        std::lock_guard<std::mutex> lock(g_imu_mutex);
        g_imu_head = g_imu_count = 0;
    }
    {
        std::lock_guard<std::mutex> lock(g_det_mutex);
        g_det_box_count = 0;
        delete[] g_det_img_buf; g_det_img_buf = nullptr;
        g_det_img_width = g_det_img_height = g_det_img_channels = 0;
        g_det_ready.store(false);
    }

    g_has_depth = g_has_disp = g_has_rect = g_has_pts = g_has_imu = g_has_det = false;
    g_calib_cached = false;
    delete g_calib; g_calib = nullptr;
    g_callback_count.store(0);
}

EXPORT int imsee_is_initialized() {
    return (g_sdk != nullptr) ? 1 : 0;
}

EXPORT int imsee_get_callback_count() {
    return g_callback_count.load();
}

// ============================================================
// Raw camera frame
// ============================================================

EXPORT void imsee_get_image_info(int* width, int* height, int* channels) {
    *width = g_frame_width;
    *height = g_frame_height;
    *channels = g_frame_channels;
}

EXPORT int imsee_get_frame(unsigned char* buffer, int buffer_size) {
    if (!g_frame_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_frame_buf == nullptr) return 0;
    int required = g_frame_width * g_frame_height * g_frame_channels;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_frame_buf, required);
    g_frame_ready.store(false);
    return required;
}

// ============================================================
// Depth
// ============================================================

// mode: 0=default, 1=high_accuracy+LR_check
EXPORT int imsee_enable_depth(int mode) {
    if (g_sdk == nullptr) return -1;

    if (g_sdk->EnableDepthProcessor()) {
        if (mode >= 1) {
            g_sdk->EnableLRConsistencyCheck();
            g_sdk->SetDepthCalMode(indem::DepthCalMode::HIGH_ACCURACY);
        }
        g_has_depth = true;
        g_sdk->RegistDepthCallback([](double time, cv::Mat depth) {
            if (depth.empty()) return;
            std::lock_guard<std::mutex> lock(g_depth_mutex);
            int w = depth.cols, h = depth.rows;
            if (g_depth_buf == nullptr || g_depth_width != w || g_depth_height != h) {
                delete[] g_depth_buf;
                g_depth_buf = new unsigned short[w * h];
                g_depth_width = w;
                g_depth_height = h;
            }
            cv::Mat depth_mm;
            depth.convertTo(depth_mm, CV_16U, 1000.0);
            memcpy(g_depth_buf, depth_mm.data, w * h * 2);
            g_depth_ready.store(true);
        });
        return 0;
    }
    return -2;
}

EXPORT int imsee_get_depth(unsigned short* buffer, int buffer_size) {
    if (!g_has_depth || !g_depth_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_depth_mutex);
    if (g_depth_buf == nullptr) return 0;
    int required = g_depth_width * g_depth_height;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_depth_buf, required * 2);
    g_depth_ready.store(false);
    return required;
}

EXPORT void imsee_get_depth_size(int* width, int* height) {
    *width = g_depth_width;
    *height = g_depth_height;
}

// ============================================================
// Disparity
// ============================================================

// mode: 0=default, 1=high_accuracy, 2=LR_check, 3=high_accuracy+LR_check
EXPORT int imsee_enable_disparity(int mode) {
    if (g_sdk == nullptr) return -1;

    if (g_sdk->EnableDisparityProcessor()) {
        if (mode == 1 || mode == 3) {
            g_sdk->SetDepthCalMode(indem::DepthCalMode::HIGH_ACCURACY);
        }
        if (mode == 2 || mode == 3) {
            g_sdk->EnableLRConsistencyCheck();
        }
        g_has_disp = true;
        g_sdk->RegistDisparityCallback([](double time, cv::Mat disparity) {
            if (disparity.empty()) return;
            std::lock_guard<std::mutex> lock(g_disp_mutex);
            int w = disparity.cols, h = disparity.rows;
            if (g_disp_buf == nullptr || g_disp_width != w || g_disp_height != h) {
                delete[] g_disp_buf;
                g_disp_buf = new float[w * h];
                g_disp_width = w;
                g_disp_height = h;
            }
            // Disparity is typically CV_32F
            if (disparity.type() == CV_32F) {
                memcpy(g_disp_buf, disparity.data, w * h * sizeof(float));
            } else {
                cv::Mat tmp;
                disparity.convertTo(tmp, CV_32F);
                memcpy(g_disp_buf, tmp.data, w * h * sizeof(float));
            }
            g_disp_ready.store(true);
        });
        return 0;
    }
    return -2;
}

EXPORT int imsee_get_disparity(float* buffer, int buffer_size) {
    if (!g_has_disp || !g_disp_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_disp_mutex);
    if (g_disp_buf == nullptr) return 0;
    int required = g_disp_width * g_disp_height;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_disp_buf, required * sizeof(float));
    g_disp_ready.store(false);
    return required;
}

EXPORT void imsee_get_disparity_size(int* width, int* height) {
    *width = g_disp_width;
    *height = g_disp_height;
}

// ============================================================
// Rectified images
// ============================================================

EXPORT int imsee_enable_rectify() {
    if (g_sdk == nullptr) return -1;

    if (g_sdk->EnableRectifyProcessor()) {
        g_has_rect = true;
        g_sdk->RegistImgCallback([](double time, cv::Mat left, cv::Mat right) {
            if (left.empty()) return;
            std::lock_guard<std::mutex> lock(g_rect_mutex);

            int lw = left.cols, lh = left.rows;
            bool has_right = !right.empty();
            int channels = left.channels();
            int out_width = has_right ? lw * 2 : lw;
            int out_size = out_width * lh * channels;

            if (g_rect_buf == nullptr || g_rect_width != out_width ||
                g_rect_height != lh || g_rect_channels != channels) {
                delete[] g_rect_buf;
                g_rect_buf = new unsigned char[out_size];
                g_rect_width = out_width;
                g_rect_height = lh;
                g_rect_channels = channels;
            }

            // Convert to grayscale if multi-channel
            cv::Mat left_gray, right_gray;
            if (channels == 3) {
                cv::cvtColor(left, left_gray, cv::COLOR_BGR2GRAY);
                if (has_right) cv::cvtColor(right, right_gray, cv::COLOR_BGR2GRAY);
                channels = 1;
                out_size = out_width * lh;
                if (g_rect_channels != 1) {
                    delete[] g_rect_buf;
                    g_rect_buf = new unsigned char[out_size];
                    g_rect_channels = 1;
                }
            } else {
                left_gray = left;
                if (has_right) right_gray = right;
            }

            // Copy left
            for (int y = 0; y < lh; y++)
                memcpy(g_rect_buf + y * out_width, left_gray.ptr(y), lw);
            // Copy right
            if (has_right)
                for (int y = 0; y < lh; y++)
                    memcpy(g_rect_buf + y * out_width + lw, right_gray.ptr(y), lw);

            g_rect_ready.store(true);
        });
        return 0;
    }
    return -2;
}

EXPORT int imsee_get_rectified(unsigned char* buffer, int buffer_size) {
    if (!g_has_rect || !g_rect_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_rect_mutex);
    if (g_rect_buf == nullptr) return 0;
    int required = g_rect_width * g_rect_height * g_rect_channels;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_rect_buf, required);
    g_rect_ready.store(false);
    return required;
}

EXPORT void imsee_get_rectified_info(int* width, int* height, int* channels) {
    *width = g_rect_width;
    *height = g_rect_height;
    *channels = g_rect_channels;
}

// ============================================================
// Point cloud
// ============================================================

EXPORT int imsee_enable_points() {
    if (g_sdk == nullptr) return -1;

    if (g_sdk->EnablePointProcessor()) {
        g_has_pts = true;
        g_sdk->RegistPointCloudCallback([](double time, cv::Mat points) {
            if (points.empty()) return;
            std::lock_guard<std::mutex> lock(g_pts_mutex);

            // points is typically CV_32FC3, rows x cols
            int w = points.cols, h = points.rows;
            int total = w * h;

            if (g_pts_buf == nullptr || g_pts_count != total) {
                delete[] g_pts_buf;
                g_pts_buf = new float[total * 3];
                g_pts_count = total;
                g_pts_width = w;
                g_pts_height = h;
            }

            if (points.type() == CV_32FC3) {
                memcpy(g_pts_buf, points.data, total * 3 * sizeof(float));
            } else {
                // Fallback: reshape to 3-channel float
                cv::Mat tmp;
                points.convertTo(tmp, CV_32FC3);
                memcpy(g_pts_buf, tmp.data, total * 3 * sizeof(float));
            }
            g_pts_ready.store(true);
        });
        return 0;
    }
    return -2;
}

EXPORT int imsee_get_points(float* buffer, int buffer_size) {
    if (!g_has_pts || !g_pts_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_pts_mutex);
    if (g_pts_buf == nullptr) return 0;
    int required = g_pts_count * 3;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_pts_buf, required * sizeof(float));
    g_pts_ready.store(false);
    return g_pts_count;
}

EXPORT void imsee_get_points_size(int* width, int* height, int* count) {
    *width = g_pts_width;
    *height = g_pts_height;
    *count = g_pts_count;
}

// ============================================================
// IMU
// ============================================================

EXPORT int imsee_enable_imu() {
    if (g_sdk == nullptr) return -1;

    g_has_imu = true;
    g_sdk->RegistModuleIMUCallback([](indem::ImuData imu) {
        std::lock_guard<std::mutex> lock(g_imu_mutex);
        ImuSample& s = g_imu_ring[g_imu_head];
        s.timestamp = imu.timestamp;
        memcpy(s.accel, imu.accel, sizeof(float) * 3);
        memcpy(s.gyro, imu.gyro, sizeof(float) * 3);
        g_imu_head = (g_imu_head + 1) % IMU_RING_SIZE;
        if (g_imu_count < IMU_RING_SIZE) g_imu_count++;
    });
    return 0;
}

// Returns number of samples copied. Each sample is 7 floats: [timestamp(as float), ax, ay, az, gx, gy, gz]
// Actually uses doubles for timestamp, so we pack as: [ts_high, ts_low, ax, ay, az, gx, gy, gz] -- too complex.
// Simpler: output buffer is double[n*7] = [timestamp, ax, ay, az, gx, gy, gz] per sample
EXPORT int imsee_get_imu(double* buffer, int max_samples) {
    if (!g_has_imu) return 0;
    std::lock_guard<std::mutex> lock(g_imu_mutex);
    if (g_imu_count == 0) return 0;

    int n = (max_samples < g_imu_count) ? max_samples : g_imu_count;
    // Read from oldest to newest
    int start;
    if (g_imu_count >= IMU_RING_SIZE) {
        start = g_imu_head;  // ring is full, head points to oldest
    } else {
        start = 0;
    }

    // Copy the most recent n samples
    int copy_start;
    if (g_imu_count >= IMU_RING_SIZE) {
        copy_start = (g_imu_head - n + IMU_RING_SIZE) % IMU_RING_SIZE;
    } else {
        copy_start = (g_imu_count >= n) ? (g_imu_count - n) : 0;
        if (g_imu_count < n) n = g_imu_count;
    }

    for (int i = 0; i < n; i++) {
        int idx = (copy_start + i) % IMU_RING_SIZE;
        double* out = buffer + i * 7;
        out[0] = g_imu_ring[idx].timestamp;
        out[1] = g_imu_ring[idx].accel[0];
        out[2] = g_imu_ring[idx].accel[1];
        out[3] = g_imu_ring[idx].accel[2];
        out[4] = g_imu_ring[idx].gyro[0];
        out[5] = g_imu_ring[idx].gyro[1];
        out[6] = g_imu_ring[idx].gyro[2];
    }

    // Reset count after reading
    g_imu_count = 0;
    g_imu_head = 0;

    return n;
}

EXPORT int imsee_get_imu_count() {
    std::lock_guard<std::mutex> lock(g_imu_mutex);
    return g_imu_count;
}

// ============================================================
// Detector
// ============================================================

EXPORT int imsee_enable_detector() {
    if (g_sdk == nullptr) return -1;

    if (g_sdk->EnableDetectorProcessor()) {
        g_has_det = true;
        g_sdk->RegistDetectorCallback([](indem::DetectorInfo info) {
            std::lock_guard<std::mutex> lock(g_det_mutex);

            // Copy boxes
            g_det_box_count = 0;
            for (const auto& bi : info.finalBoxInfo) {
                if (g_det_box_count >= 256) break;
                DetBox& db = g_det_boxes[g_det_box_count];
                db.x = bi.box.x;
                db.y = bi.box.y;
                db.w = bi.box.width;
                db.h = bi.box.height;
                db.score = bi.score;
                db.class_id = (int)bi.class_name;
                g_det_box_count++;
            }

            // Copy image
            if (!info.img.empty()) {
                int w = info.img.cols, h = info.img.rows;
                int ch = info.img.channels();
                int size = w * h * ch;

                if (g_det_img_buf == nullptr || g_det_img_width != w ||
                    g_det_img_height != h || g_det_img_channels != ch) {
                    delete[] g_det_img_buf;
                    g_det_img_buf = new unsigned char[size];
                    g_det_img_width = w;
                    g_det_img_height = h;
                    g_det_img_channels = ch;
                }
                memcpy(g_det_img_buf, info.img.data, size);
            }

            g_det_ready.store(true);
        });
        return 0;
    }
    return -2;
}

// Output: buffer is int[n*6] = [x, y, w, h, class_id, score_x1000] per box
EXPORT int imsee_get_detector_boxes(int* buffer, int max_boxes) {
    if (!g_has_det || !g_det_ready.load()) return 0;
    std::lock_guard<std::mutex> lock(g_det_mutex);

    int n = g_det_box_count;
    if (n > max_boxes) n = max_boxes;

    for (int i = 0; i < n; i++) {
        int* out = buffer + i * 6;
        out[0] = g_det_boxes[i].x;
        out[1] = g_det_boxes[i].y;
        out[2] = g_det_boxes[i].w;
        out[3] = g_det_boxes[i].h;
        out[4] = g_det_boxes[i].class_id;
        out[5] = (int)(g_det_boxes[i].score * 1000);
    }
    g_det_ready.store(false);
    return n;
}

EXPORT int imsee_get_detector_image(unsigned char* buffer, int buffer_size) {
    if (!g_has_det) return 0;
    std::lock_guard<std::mutex> lock(g_det_mutex);
    if (g_det_img_buf == nullptr) return 0;
    int required = g_det_img_width * g_det_img_height * g_det_img_channels;
    if (buffer_size < required) return -1;
    memcpy(buffer, g_det_img_buf, required);
    return required;
}

EXPORT void imsee_get_detector_image_info(int* width, int* height, int* channels) {
    *width = g_det_img_width;
    *height = g_det_img_height;
    *channels = g_det_img_channels;
}

// ============================================================
// Calibration / Device info
// ============================================================

static void ensure_calib() {
    if (!g_calib_cached && g_sdk != nullptr) {
        if (g_calib == nullptr) g_calib = new indem::MoudleAllParam();
        *g_calib = g_sdk->GetModuleParams();
        g_calib_cached = true;
    }
}

// Returns JSON-like string with calibration parameters
EXPORT const char* imsee_get_calibration() {
    static char buf[4096];
    if (g_sdk == nullptr) {
        strcpy(buf, "{}");
        return buf;
    }
    ensure_calib();
    if (g_calib == nullptr) { strcpy(buf, "{}"); return buf; }

    // Find the camera params for current resolution
    indem::CameraParameter left, right;
    bool found = false;

    auto it640_l = g_calib->_left_camera.find(indem::RES_640X400);
    auto it640_r = g_calib->_right_camera.find(indem::RES_640X400);
    if (it640_l != g_calib->_left_camera.end() && it640_r != g_calib->_right_camera.end()) {
        left = it640_l->second;
        right = it640_r->second;
        found = true;
    }
    if (!found) {
        auto it1280_l = g_calib->_left_camera.find(indem::RES_1280X800);
        auto it1280_r = g_calib->_right_camera.find(indem::RES_1280X800);
        if (it1280_l != g_calib->_left_camera.end() && it1280_r != g_calib->_right_camera.end()) {
            left = it1280_l->second;
            right = it1280_r->second;
            found = true;
        }
    }

    if (!found) {
        strcpy(buf, "{}");
        return buf;
    }

    snprintf(buf, sizeof(buf),
        "{"
        "\"baseline\":%.6f,"
        "\"left\":{\"w\":%d,\"h\":%d,\"fx\":%.6f,\"fy\":%.6f,\"cx\":%.6f,\"cy\":%.6f,"
        "\"k1\":%.8f,\"k2\":%.8f,\"t1\":%.8f,\"t2\":%.8f,"
        "\"P\":[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]},"
        "\"right\":{\"w\":%d,\"h\":%d,\"fx\":%.6f,\"fy\":%.6f,\"cx\":%.6f,\"cy\":%.6f,"
        "\"k1\":%.8f,\"k2\":%.8f,\"t1\":%.8f,\"t2\":%.8f,"
        "\"P\":[%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f]}"
        "}",
        g_calib->_baseline,
        left._width, left._height, left._focal_length[0], left._focal_length[1],
        left._principal_point[0], left._principal_point[1],
        left._D[0], left._D[1], left._D[2], left._D[3],
        left._P[0], left._P[1], left._P[2], left._P[3],
        left._P[4], left._P[5], left._P[6], left._P[7],
        left._P[8], left._P[9], left._P[10], left._P[11],
        right._width, right._height, right._focal_length[0], right._focal_length[1],
        right._principal_point[0], right._principal_point[1],
        right._D[0], right._D[1], right._D[2], right._D[3],
        right._P[0], right._P[1], right._P[2], right._P[3],
        right._P[4], right._P[5], right._P[6], right._P[7],
        right._P[8], right._P[9], right._P[10], right._P[11]
    );
    return buf;
}

EXPORT const char* imsee_get_device_info_detailed() {
    static char buf[2048];
    if (g_sdk == nullptr) {
        strcpy(buf, "{}");
        return buf;
    }
    indem::ModuleInfo mi = g_sdk->GetModuleInfo();
    ensure_calib();

    double baseline_m = g_calib ? g_calib->_baseline : 0.0;
    int cam_ch = g_calib ? g_calib->_camera_channel : 1;

    snprintf(buf, sizeof(buf),
        "{"
        "\"id\":\"%.31s\","
        "\"designer\":\"%.31s\","
        "\"firmware\":\"%.31s\","
        "\"hardware\":\"%.31s\","
        "\"lens\":\"%.31s\","
        "\"imu\":\"%.31s\","
        "\"viewing_angle\":\"%.31s\","
        "\"baseline\":\"%.31s\","
        "\"baseline_m\":%.6f,"
        "\"camera_channel\":%d"
        "}",
        mi._id, mi._designer, mi._fireware_version, mi._hardware_version,
        mi._lens, mi._imu, mi._viewing_angle, mi._baseline,
        baseline_m, cam_ch
    );
    return buf;
}

EXPORT const char* imsee_get_module_info() {
    static char info[256];
    if (g_sdk == nullptr) {
        strcpy(info, "Camera not initialized");
        return info;
    }
    indem::ModuleInfo mi = g_sdk->GetModuleInfo();
    snprintf(info, sizeof(info), "ID: %.32s, FW: %.32s", mi._id, mi._fireware_version);
    return info;
}

}  // extern "C"
