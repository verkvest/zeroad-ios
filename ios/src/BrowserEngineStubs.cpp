/* Copyright (C) 2026 verkvest. GPL-2.0-or-later.
 * SpiderMonkey's mozglue references BrowserEngineCore's JIT write-protection helpers
 * (iOS 17.4+). This port runs SpiderMonkey without any JIT, so they are never called;
 * App Store rejects apps linking BrowserEngineCore (ITMS-91017), so provide inert stubs
 * instead of linking the framework. */
#include "lib/sysdep/os.h"
#if OS_IOS
extern "C" {
void be_memory_inline_jit_restrict_rwx_to_rw_with_witness_impl(void) {}
void be_memory_inline_jit_restrict_rwx_to_rx_with_witness_impl(void) {}
int be_memory_inline_jit_restrict_with_witness_supported(void) { return 0; }
}
#endif
