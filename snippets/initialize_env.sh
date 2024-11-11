#!/bin/sh
OCI_ENTRYPOINT='"/usr/local/bin/entrypoint.sh"'
OCI_CMD='"/bin/bash"'

# When SINGULARITY_NO_EVAL set, use OCI compatible behavior that does
# not evaluate resolved CMD / ENTRYPOINT / ARGS through the shell, and
# does not modify expected quoting behavior of args.
if [ -n "$SINGULARITY_NO_EVAL" ]; then
	# ENTRYPOINT only - run entrypoint plus args
	if [ -z "$OCI_CMD" ] && [ -n "$OCI_ENTRYPOINT" ]; then
		set -- '/usr/local/bin/entrypoint.sh' "$@"

		exec "$@"
	fi

	# CMD only - run CMD or override with args
	if [ -n "$OCI_CMD" ] && [ -z "$OCI_ENTRYPOINT" ]; then
		if [ $# -eq 0 ]; then
			set -- '/bin/bash' "$@"

			:
		fi
		exec "$@"
	fi

	# ENTRYPOINT and CMD - run ENTRYPOINT with CMD as default args
	# override with user provided args
	if [ $# -gt 0 ]; then
		set -- '/usr/local/bin/entrypoint.sh' "$@"

		:
	else
		set -- '/bin/bash' "$@"

		set -- '/usr/local/bin/entrypoint.sh' "$@"

		:
	fi
	exec "$@"
fi

# Standard Singularity behavior evaluates CMD / ENTRYPOINT / ARGS
# combination through shell before exec, and requires special quoting
# due to concatenation of CMDLINE_ARGS.
CMDLINE_ARGS=""
# prepare command line arguments for evaluation
for arg in "$@"; do
		CMDLINE_ARGS="${CMDLINE_ARGS} \"$arg\""
done

# ENTRYPOINT only - run entrypoint plus args
if [ -z "$OCI_CMD" ] && [ -n "$OCI_ENTRYPOINT" ]; then
	if [ $# -gt 0 ]; then
		SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${CMDLINE_ARGS}"
	else
		SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT}"
	fi
fi

# CMD only - run CMD or override with args
if [ -n "$OCI_CMD" ] && [ -z "$OCI_ENTRYPOINT" ]; then
	if [ $# -gt 0 ]; then
		SINGULARITY_OCI_RUN="${CMDLINE_ARGS}"
	else
		SINGULARITY_OCI_RUN="${OCI_CMD}"
	fi
fi

# ENTRYPOINT and CMD - run ENTRYPOINT with CMD as default args
# override with user provided args
if [ $# -gt 0 ]; then
	SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${CMDLINE_ARGS}"
else
	SINGULARITY_OCI_RUN="${OCI_ENTRYPOINT} ${OCI_CMD}"
fi

# Evaluate shell expressions first and set arguments accordingly,
# then execute final command as first container process
eval "set ${SINGULARITY_OCI_RUN}"
exec "$@"

