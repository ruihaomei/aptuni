#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/attr.h>
#include <sys/clonefile.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <unistd.h>

/*
 * macOS-only S04 bridge for positive APFS full-clone mapping evidence.
 *
 * Paths and native identifiers never enter stdout. The caller receives only
 * booleans and fixed reason codes. An absent signal is deliberately not a
 * confinement proof; unsupported or incomplete observations are unverified.
 */

typedef struct {
    uint64_t clone_id;
    uint64_t extended_flags;
    uint32_t clone_refcount;
    dev_t device;
    ino_t inode;
} file_snapshot_t;

typedef struct {
    bool query_complete;
    bool valid_bit;
    bool present_bit;
} volume_mapping_t;

static void print_unverified(const char *reason) {
    printf("{\"status\":\"unverified\",\"reason_code\":\"%s\"}\n", reason);
}

static bool read_bytes(
    const unsigned char *buffer,
    size_t buffer_length,
    size_t *offset,
    void *destination,
    size_t destination_length
) {
    if (*offset > buffer_length || destination_length > buffer_length - *offset) {
        return false;
    }
    memcpy(destination, buffer + *offset, destination_length);
    *offset += destination_length;
    return true;
}

static volume_mapping_t volume_full_clone_mapping(int fd) {
    struct attrlist attributes = {0};
    struct statfs filesystem = {0};
    unsigned char buffer[128] = {0};
    uint32_t returned_length = 0;
    vol_capabilities_attr_t capabilities = {0};
    size_t offset = 0;

    attributes.bitmapcount = ATTR_BIT_MAP_COUNT;
    attributes.volattr = ATTR_VOL_INFO | ATTR_VOL_CAPABILITIES;
    volume_mapping_t result = {0};
    if (fstatfs(fd, &filesystem) != 0 ||
        getattrlist(filesystem.f_mntonname, &attributes, buffer,
                    sizeof(buffer), FSOPT_ATTR_CMN_EXTENDED) != 0) {
        return result;
    }
    if (!read_bytes(buffer, sizeof(buffer), &offset, &returned_length,
                    sizeof(returned_length)) ||
        returned_length > sizeof(buffer) ||
        !read_bytes(buffer, returned_length, &offset, &capabilities,
                    sizeof(capabilities))) {
        return result;
    }
    uint32_t valid = capabilities.valid[VOL_CAPABILITIES_FORMAT];
    uint32_t present = capabilities.capabilities[VOL_CAPABILITIES_FORMAT];
    result.query_complete = true;
    result.valid_bit = (valid & VOL_CAP_FMT_CLONE_MAPPING) != 0;
    result.present_bit = (present & VOL_CAP_FMT_CLONE_MAPPING) != 0;
    return result;
}

static bool snapshot_file(int fd, file_snapshot_t *snapshot) {
    struct attrlist attributes = {0};
    unsigned char buffer[128] = {0};
    uint32_t returned_length = 0;
    attribute_set_t returned = {0};
    struct stat metadata = {0};
    size_t offset = 0;
    const uint32_t requested = ATTR_CMNEXT_CLONEID |
                               ATTR_CMNEXT_EXT_FLAGS |
                               ATTR_CMNEXT_CLONE_REFCNT;

    if (fstat(fd, &metadata) != 0 || !S_ISREG(metadata.st_mode)) {
        return false;
    }
    attributes.bitmapcount = ATTR_BIT_MAP_COUNT;
    attributes.commonattr = ATTR_CMN_RETURNED_ATTRS;
    attributes.forkattr = requested;
    if (fgetattrlist(fd, &attributes, buffer, sizeof(buffer),
                     FSOPT_ATTR_CMN_EXTENDED) != 0) {
        return false;
    }
    if (!read_bytes(buffer, sizeof(buffer), &offset, &returned_length,
                    sizeof(returned_length)) ||
        returned_length > sizeof(buffer) ||
        !read_bytes(buffer, returned_length, &offset, &returned,
                    sizeof(returned)) ||
        (returned.commonattr & ATTR_CMN_RETURNED_ATTRS) == 0 ||
        (returned.forkattr & requested) != requested ||
        !read_bytes(buffer, returned_length, &offset, &snapshot->clone_id,
                    sizeof(snapshot->clone_id)) ||
        !read_bytes(buffer, returned_length, &offset, &snapshot->extended_flags,
                    sizeof(snapshot->extended_flags)) ||
        !read_bytes(buffer, returned_length, &offset, &snapshot->clone_refcount,
                    sizeof(snapshot->clone_refcount))) {
        return false;
    }
    snapshot->device = metadata.st_dev;
    snapshot->inode = metadata.st_ino;
    return true;
}

static bool is_full_clone_family(
    const file_snapshot_t *left,
    const file_snapshot_t *right
) {
    bool same_object = left->device == right->device &&
                       left->inode == right->inode;
    bool same_volume = left->device == right->device;
    bool same_clone_id = same_volume && left->clone_id != 0 &&
                         left->clone_id == right->clone_id;
    bool both_share_all =
        (left->extended_flags & EF_SHARES_ALL_BLOCKS) != 0 &&
        (right->extended_flags & EF_SHARES_ALL_BLOCKS) != 0;
    bool refcounts_confirm = left->clone_refcount >= 2 &&
                             right->clone_refcount >= 2;
    return !same_object && same_clone_id && both_share_all && refcounts_confirm;
}

static int compare_files(const char *left_path, const char *right_path) {
    int left_fd = open(
        left_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK
    );
    int right_fd = open(
        right_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK
    );
    if (left_fd < 0 || right_fd < 0) {
        if (left_fd >= 0) {
            close(left_fd);
        }
        if (right_fd >= 0) {
            close(right_fd);
        }
        print_unverified("file_open_failed");
        return 2;
    }

    file_snapshot_t left = {0};
    file_snapshot_t right = {0};
    volume_mapping_t left_volume = volume_full_clone_mapping(left_fd);
    volume_mapping_t right_volume = volume_full_clone_mapping(right_fd);
    bool snapshots_complete = snapshot_file(left_fd, &left) &&
                              snapshot_file(right_fd, &right);
    close(left_fd);
    close(right_fd);

    if (!snapshots_complete) {
        print_unverified("native_attributes_incomplete");
        return 0;
    }
    if (!left_volume.query_complete || !right_volume.query_complete) {
        print_unverified("volume_capability_query_failed");
        return 0;
    }
    if (!left_volume.valid_bit || !right_volume.valid_bit) {
        print_unverified("volume_clone_mapping_capability_invalid");
        return 0;
    }
    if (!left_volume.present_bit || !right_volume.present_bit) {
        print_unverified("volume_clone_mapping_unsupported");
        return 0;
    }
    bool same_object = left.device == right.device && left.inode == right.inode;
    bool same_volume = left.device == right.device;
    bool same_clone_id = same_volume && left.clone_id != 0 &&
                         left.clone_id == right.clone_id;
    bool both_share_all =
        (left.extended_flags & EF_SHARES_ALL_BLOCKS) != 0 &&
        (right.extended_flags & EF_SHARES_ALL_BLOCKS) != 0;
    bool refcounts_confirm = left.clone_refcount >= 2 &&
                             right.clone_refcount >= 2;
    bool full_clone_family = is_full_clone_family(&left, &right);
    const char *reason = full_clone_family
        ? "full_clone_mapping_positive"
        : (same_object ? "same_object" : "full_clone_mapping_absent");

    printf(
        "{\"status\":\"ok\",\"same_object\":%s,"
        "\"same_volume\":%s,\"same_clone_id\":%s,"
        "\"both_share_all_blocks\":%s,\"refcounts_confirm\":%s,"
        "\"full_clone_family\":%s,\"reason_code\":\"%s\"}\n",
        same_object ? "true" : "false",
        same_volume ? "true" : "false",
        same_clone_id ? "true" : "false",
        both_share_all ? "true" : "false",
        refcounts_confirm ? "true" : "false",
        full_clone_family ? "true" : "false",
        reason
    );
    return 0;
}

static int run_self_test(void) {
    file_snapshot_t source = {
        .clone_id = 77,
        .extended_flags = EF_SHARES_ALL_BLOCKS,
        .clone_refcount = 2,
        .device = 3,
        .inode = 10,
    };
    file_snapshot_t clone = source;
    clone.inode = 11;
    if (!is_full_clone_family(&source, &clone)) {
        print_unverified("self_test_positive_failed");
        return 2;
    }
    file_snapshot_t same_object = source;
    file_snapshot_t different_id = clone;
    different_id.clone_id = 78;
    file_snapshot_t partial = clone;
    partial.extended_flags = EF_MAY_SHARE_BLOCKS;
    file_snapshot_t insufficient_refs = clone;
    insufficient_refs.clone_refcount = 1;
    file_snapshot_t other_volume = clone;
    other_volume.device = 4;
    if (is_full_clone_family(&source, &same_object) ||
        is_full_clone_family(&source, &different_id) ||
        is_full_clone_family(&source, &partial) ||
        is_full_clone_family(&source, &insufficient_refs) ||
        is_full_clone_family(&source, &other_volume)) {
        print_unverified("self_test_negative_failed");
        return 2;
    }
    printf("{\"status\":\"ok\",\"reason_code\":\"self_test_passed\"}\n");
    return 0;
}

static int clone_for_test(const char *source, const char *destination) {
    if (clonefile(source, destination, CLONE_NOFOLLOW) != 0) {
        print_unverified("clonefile_failed");
        return 2;
    }
    printf("{\"status\":\"ok\",\"reason_code\":\"clone_created\"}\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "self-test") == 0) {
        return run_self_test();
    }
    if (argc == 4 && strcmp(argv[1], "compare") == 0) {
        return compare_files(argv[2], argv[3]);
    }
    if (argc == 4 && strcmp(argv[1], "clone-for-test") == 0) {
        return clone_for_test(argv[2], argv[3]);
    }
    print_unverified("invalid_invocation");
    return 2;
}
