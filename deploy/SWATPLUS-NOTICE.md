# SWAT+ runtime included in the backend image

The backend image includes the Linux SWAT+ 61.0.2.61 research build and South
Fork model inputs used by the coupling adapter. It is a custom build, not an
official SWAT+ release. The build adds daily channel-storage output used by the
coupling workflow.

The original source is available at the exact upstream commit
[`77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d`](https://github.com/swat-model/swatplus/tree/77b722bac716c32f2fba6b4e3f9dd6ea4b008e3d).
The two local source changes are recorded in
[`SWATPLUS-SOURCE-CHANGES.patch`](../licenses/SWATPLUS-SOURCE-CHANGES.patch).
The upstream project is distributed under LGPL-2.1; its license text is kept
at [`licenses/SWATPLUS-LGPL-2.1.txt`](../licenses/SWATPLUS-LGPL-2.1.txt).

The compressed deployment archive is pinned by `swat-runtime.sha256`. The
Docker build verifies that checksum and installs the archive into
`backend/data/swat-runtime` before the service starts.
