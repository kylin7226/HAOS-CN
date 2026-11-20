#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>

typedef uint32_t u32;
#define U32_MAX UINT32_MAX
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define MPP_MAX_MSG_NUM 16
#define MPP_CMD_SET_REG_WRITE 1
#define MPP_CMD_SET_REG_READ 2
#define MPP_CMD_SET_REG_ADDR_OFFSET 3
#define MPP_CMD_SET_RCB_INFO 4
#define mpp_err(...) ((void)0)
#define mpp_debug(...) ((void)0)
#define mpp_debug_enter() ((void)0)

struct mpp_request { u32 cmd, offset, size; void *data; };
struct reg_offset_elem { u32 index, offset; };
struct reg_offset_info { u32 cnt; struct reg_offset_elem elem[4]; };
struct mpp_session { void *priv; };
struct rkvenc_hw_info { u32 reg_class; };
struct rkvenc2_session_priv { int rcb_inf; };
struct mpp_task_msgs { u32 req_cnt; struct mpp_request reqs[MPP_MAX_MSG_NUM]; };
struct rkvenc_task {
    struct rkvenc_hw_info *hw_info;
    struct mpp_request w_reqs[MPP_MAX_MSG_NUM], r_reqs[MPP_MAX_MSG_NUM];
    u32 w_req_cnt, r_req_cnt;
    struct { int valid; } reg[MPP_MAX_MSG_NUM + 1];
    struct reg_offset_info off_inf;
};

static int copies, copy_failure, freed;
static unsigned char registers[64];
static int copy_from_user(void *dst, const void *src, size_t size)
{
    copies++;
    if (copy_failure)
        return 1;
    memcpy(dst, src, size);
    return 0;
}
static int req_over_class(struct mpp_request *req, struct rkvenc_task *task, int c)
{
    return 1;
}
static int rkvenc_alloc_class_msg(struct rkvenc_task *task, int c) { return 0; }
static void rkvenc_update_req(struct rkvenc_task *task, int c,
                              struct mpp_request *in, struct mpp_request *out)
{
    *out = *in;
}
static void *rkvenc_get_class_reg(struct rkvenc_task *task, u32 offset)
{
    return registers;
}
static void rkvenc_free_class_msg(struct rkvenc_task *task) { freed++; }
static void rkvenc2_extract_rcb_info(int *info, struct mpp_request *req) { }

/* DRIVER_FUNCTIONS */

int main(void)
{
    struct mpp_request req = {0};
    for (u32 offset = 0; offset <= 80; offset++) {
        for (u32 size = 0; size <= 128; size++) {
            req.offset = offset;
            req.size = size;
            int ret = mpp_check_req(&req, 0, 64, 0, 64);
            if (offset > 64) {
                assert(ret == -EINVAL);
            } else {
                assert(ret == 0);
                assert(req.size == (size < 64 - offset ? size : 64 - offset));
            }
        }
    }
    req.offset = 0x80000000;
    req.size = 1;
    assert(mpp_check_req(&req, 0, 64, 0, 64) == -EINVAL);
    req.offset = 16;
    req.size = U32_MAX;
    assert(mpp_check_req(&req, 0, 64, 0, 64) == -EINVAL);
    req.offset = 3;
    req.size = 4;
    assert(mpp_check_req(&req, 4, 64, 0, 64) == -EINVAL);
    req.offset = 12;
    req.size = 64;
    assert(mpp_check_req(&req, 4, 64, 0, 64) == 0 && req.size == 56);

    struct reg_offset_elem elements[4] = {{1, 2}, {2, 3}, {3, 4}, {0, 5}};
    struct reg_offset_info info = {0};
    req.data = elements;
    req.size = sizeof(elements);
    assert(mpp_extract_reg_offset_info(&info, &req) == 0);
    assert(info.cnt == 4 && !memcmp(info.elem, elements, sizeof(elements)));
    copies = 0;
    req.size = 1;
    assert(mpp_extract_reg_offset_info(&info, &req) == -EINVAL && copies == 0);
    req.size = sizeof(elements[0]);
    assert(mpp_extract_reg_offset_info(&info, &req) == -EINVAL && copies == 0);
    info.cnt = 0;
    req.size = U32_MAX - 7;
    assert(mpp_extract_reg_offset_info(&info, &req) == -EINVAL && copies == 0);
    req.size = sizeof(elements[0]);
    copy_failure = 1;
    assert(mpp_extract_reg_offset_info(&info, &req) == -EINVAL && info.cnt == 0);
    copy_failure = 0;

    struct mpp_session session = {0};
    struct rkvenc_hw_info hw = {MPP_MAX_MSG_NUM};
    struct mpp_task_msgs msgs = {.req_cnt = 1};
    msgs.reqs[0] = (struct mpp_request){.cmd = MPP_CMD_SET_REG_WRITE,
                                      .size = 1, .data = elements};
    for (u32 cmd = MPP_CMD_SET_REG_WRITE; cmd <= MPP_CMD_SET_REG_READ; cmd++) {
        struct rkvenc_task task = {.hw_info = &hw};
        hw.reg_class = MPP_MAX_MSG_NUM;
        msgs.reqs[0].cmd = cmd;
        freed = 0;
        assert(rkvenc_extract_task_msg(&session, &task, &msgs) == 0);
        assert(freed == 0);
        assert((cmd == MPP_CMD_SET_REG_WRITE ? task.w_req_cnt : task.r_req_cnt) == 16);
        task = (struct rkvenc_task){.hw_info = &hw};
        hw.reg_class = MPP_MAX_MSG_NUM + 1;
        assert(rkvenc_extract_task_msg(&session, &task, &msgs) == -EINVAL);
        assert(freed == 1);
        assert((cmd == MPP_CMD_SET_REG_WRITE ? task.w_req_cnt : task.r_req_cnt) == 16);
    }
    struct rkvenc_task task = {.hw_info = &hw};
    msgs.reqs[0].cmd = MPP_CMD_SET_REG_ADDR_OFFSET;
    freed = 0;
    assert(rkvenc_extract_task_msg(&session, &task, &msgs) == -EINVAL);
    assert(freed == 1);
    return 0;
}
