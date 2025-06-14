from typing import Any, Dict

from codelyzer.console import logger, debug, debug_log
from codelyzer.metrics import FileMetrics, ProjectMetrics, MetricProvider, SecurityLevel


class SecurityAnalyzer(MetricProvider):
    """Analyzer for identifying security issues in code"""

    def __init__(self) -> None:
        """Initialize security analyzer"""
        super().__init__()
        logger.debug("SecurityAnalyzer initialized")

    @debug
    def analyze_file(self, file_metrics: FileMetrics, file_content: str, ast_data: Any) -> None:
        """Analyze file for security issues and update metrics"""
        language = file_metrics.language
        logger.debug(f"Analyzing security issues in {file_metrics.file_path} ({language})")

        # Skip if content is empty
        if not file_content:
            logger.debug(f"Skipping security analysis for {file_metrics.file_path} - empty content")
            return

        # Analyze based on language
        if language == "python":
            self._analyze_python_security(file_metrics, file_content, ast_data)
        elif language in ("javascript", "typescript", "jsx"):
            self._analyze_js_security(file_metrics, file_content, ast_data)
        else:
            debug_log(f"No specific security analyzer for language: {language}")
        # Add other languages as needed

    @debug
    def analyze_project(self, project_metrics: ProjectMetrics) -> None:
        """Analyze project-level security metrics"""
        logger.info("Analyzing project-level security metrics")
        
        # Aggregate vulnerabilities by type
        vulnerability_types = {}

        for file_metrics in project_metrics.file_metrics:
            for vuln in file_metrics.security_issues:
                vuln_type = vuln.get('type', 'unknown')
                if vuln_type not in vulnerability_types:
                    vulnerability_types[vuln_type] = 0
                vulnerability_types[vuln_type] += 1

        # Add aggregated data to project metrics
        project_metrics.security.vulnerability_types = vulnerability_types
        
        # Log summary of findings
        total_issues = sum(vulnerability_types.values())
        logger.info(f"Found {total_issues} security issues across {len(vulnerability_types)} vulnerability types")
        for vuln_type, count in sorted(vulnerability_types.items(), key=lambda x: x[1], reverse=True):
            logger.debug(f"Security issue type: {vuln_type} - {count} occurrences")

    @debug
    def _analyze_python_security(self, file_metrics: FileMetrics, file_content: str, ast_data: Any) -> None:
        """Analyze Python code for security issues"""
        logger.debug(f"Running Python security checks on {file_metrics.file_path}")
        
        # Check for common Python security issues
        self._check_for_os_command_injection(file_metrics, file_content)
        self._check_for_sql_injection(file_metrics, file_content)
        self._check_for_insecure_deserialization(file_metrics, file_content)
        self._check_for_hardcoded_secrets(file_metrics, file_content)
        
        logger.debug(f"Python security analysis complete: found {len(file_metrics.security_issues)} issues")

    @debug
    def _analyze_js_security(self, file_metrics: FileMetrics, file_content: str, ast_data: Any) -> None:
        """Analyze JavaScript/TypeScript code for security issues"""
        logger.debug(f"Running JavaScript security checks on {file_metrics.file_path}")
        
        # Check for common JavaScript security issues
        self._check_for_eval(file_metrics, file_content)
        self._check_for_document_write(file_metrics, file_content)
        self._check_for_innerhtml(file_metrics, file_content)
        self._check_for_hardcoded_secrets(file_metrics, file_content)
        
        logger.debug(f"JavaScript security analysis complete: found {len(file_metrics.security_issues)} issues")

    def _check_for_os_command_injection(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for OS command injection vulnerabilities"""
        debug_log(f"Checking for OS command injection in {file_metrics.file_path}")
        patterns = [
            r"os\.system\((?!['\"]\w+['\"])[^\)]*\)",
            r"subprocess\.call\((?!['\"]\w+['\"])[^\)]*\)",
            r"subprocess\.Popen\((?!['\"]\w+['\"])[^\)]*\)",
            r"eval\([^\)]*\)"
        ]

        issues_found = 0
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, file_content)
            for match in matches:
                location = self._get_line_number(file_content, match.start())
                debug_log(f"Found OS command injection at line {location['line']}: {match.group(0)}")
                self._add_vulnerability(
                    file_metrics,
                    "os_command_injection",
                    f"Possible command injection at line {location['line']}",
                    location,
                    SecurityLevel.HIGH_RISK
                )
                issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} potential OS command injection issues")

    def _check_for_sql_injection(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for SQL injection vulnerabilities"""
        debug_log(f"Checking for SQL injection in {file_metrics.file_path}")
        patterns = [
            r"execute\([^,]*\+[^\)]*\)",
            r"execute\([^,]*%[^\)]*\)",
            r"execute\([^,]*f['\"][^'\"]*{[^}]*}[^'\"]*['\"]",
            r"cursor\.execute\([^,]*\+[^\)]*\)"
        ]

        issues_found = 0
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, file_content)
            for match in matches:
                location = self._get_line_number(file_content, match.start())
                debug_log(f"Found SQL injection at line {location['line']}: {match.group(0)}")
                self._add_vulnerability(
                    file_metrics,
                    "sql_injection",
                    f"Possible SQL injection at line {location['line']}",
                    location,
                    SecurityLevel.CRITICAL
                )
                issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} potential SQL injection issues")

    def _check_for_eval(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for unsafe eval() usage in JavaScript"""
        debug_log(f"Checking for unsafe eval() in {file_metrics.file_path}")
        pattern = r"eval\([^\)]+\)"
        
        import re
        matches = re.finditer(pattern, file_content)
        issues_found = 0
        for match in matches:
            location = self._get_line_number(file_content, match.start())
            debug_log(f"Found unsafe eval() at line {location['line']}: {match.group(0)}")
            self._add_vulnerability(
                file_metrics,
                "unsafe_eval",
                f"Unsafe eval() usage at line {location['line']}",
                location,
                SecurityLevel.HIGH_RISK
            )
            issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} unsafe eval() usages")

    def _check_for_document_write(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for unsafe document.write usage in JavaScript"""
        debug_log(f"Checking for document.write in {file_metrics.file_path}")
        pattern = r"document\.write\([^\)]+\)"
        
        import re
        matches = re.finditer(pattern, file_content)
        issues_found = 0
        for match in matches:
            location = self._get_line_number(file_content, match.start())
            debug_log(f"Found document.write() at line {location['line']}: {match.group(0)}")
            self._add_vulnerability(
                file_metrics,
                "document_write",
                f"Unsafe document.write() at line {location['line']}",
                location,
                SecurityLevel.MEDIUM_RISK
            )
            issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} document.write() usages")

    def _check_for_innerhtml(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for unsafe innerHTML usage in JavaScript"""
        debug_log(f"Checking for innerHTML in {file_metrics.file_path}")
        pattern = r"\.innerHTML\s*=\s*[^;]+"
        
        import re
        matches = re.finditer(pattern, file_content)
        issues_found = 0
        for match in matches:
            location = self._get_line_number(file_content, match.start())
            debug_log(f"Found innerHTML usage at line {location['line']}: {match.group(0)}")
            self._add_vulnerability(
                file_metrics,
                "innerhtml",
                f"Potentially unsafe innerHTML usage at line {location['line']}",
                location,
                SecurityLevel.MEDIUM_RISK
            )
            issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} potentially unsafe innerHTML usages")

    def _check_for_insecure_deserialization(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for insecure deserialization"""
        debug_log(f"Checking for insecure deserialization in {file_metrics.file_path}")
        patterns = [
            r"pickle\.loads\(",
            r"pickle\.load\(",
            r"yaml\.load\([^,)]*\)",  # Missing safe_load
            r"marshal\.loads\("
        ]

        issues_found = 0
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, file_content)
            for match in matches:
                location = self._get_line_number(file_content, match.start())
                debug_log(f"Found insecure deserialization at line {location['line']}: {match.group(0)}")
                self._add_vulnerability(
                    file_metrics,
                    "insecure_deserialization",
                    f"Insecure deserialization at line {location['line']}",
                    location,
                    SecurityLevel.HIGH_RISK
                )
                issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} insecure deserialization issues")

    def _check_for_hardcoded_secrets(self, file_metrics: FileMetrics, file_content: str) -> None:
        """Check for hardcoded secrets in code"""
        debug_log(f"Checking for hardcoded secrets in {file_metrics.file_path}")
        patterns = [
            r"password\s*=\s*['\"][^'\"]+['\"]",
            r"api[_]?key\s*=\s*['\"][^'\"]+['\"]",
            r"secret\s*=\s*['\"][^'\"]+['\"]",
            r"token\s*=\s*['\"][^'\"]+['\"]"
        ]

        issues_found = 0
        for pattern in patterns:
            import re
            matches = re.finditer(pattern, file_content, re.IGNORECASE)
            for match in matches:
                # Ignore if it looks like an environment variable
                if "os.environ" in match.group(0) or "process.env" in match.group(0):
                    continue

                location = self._get_line_number(file_content, match.start())
                # Don't log the actual secret, just the pattern found
                pattern_found = match.group(0).split("=")[0].strip()
                debug_log(f"Found potential hardcoded secret at line {location['line']}: {pattern_found}")
                self._add_vulnerability(
                    file_metrics,
                    "hardcoded_secret",
                    f"Possible hardcoded secret at line {location['line']}",
                    location,
                    SecurityLevel.HIGH_RISK
                )
                issues_found += 1
        
        if issues_found:
            logger.debug(f"Found {issues_found} potential hardcoded secrets")

    @staticmethod
    def _get_line_number(content: str, position: int) -> Dict:
        """Get line number from position in the content"""
        lines = content[:position].split('\n')
        line = len(lines)
        column = len(lines[-1]) + 1
        return {
            'line': line,
            'column': column,
            'position': position
        }

    def _add_vulnerability(
            self,
            file_metrics: FileMetrics,
            vuln_type: str,
            message: str,
            location: Dict,
            level: SecurityLevel = SecurityLevel.MEDIUM_RISK
    ) -> None:
        """Add a vulnerability to the file metrics"""
        vulnerability = {
            'type': vuln_type,
            'message': message,
            'location': location,
            'level': level,
            'severity': self._level_to_severity(level)
        }

        file_metrics.security.vulnerabilities.append(vulnerability)
        
        severity = self._level_to_severity(level)
        logger.debug(f"Added {severity} security vulnerability: {message}")

        # Adjust security score based on severity
        if level == SecurityLevel.CRITICAL:
            file_metrics.security.security_score -= 25
        elif level == SecurityLevel.HIGH_RISK:
            file_metrics.security.security_score -= 15
        elif level == SecurityLevel.MEDIUM_RISK:
            file_metrics.security.security_score -= 5
        elif level == SecurityLevel.LOW_RISK:
            file_metrics.security.security_score -= 1

        file_metrics.security.security_score = max(0.0, file_metrics.security.security_score)
        debug_log(f"Updated security score: {file_metrics.security.security_score}")

    @staticmethod
    def _level_to_severity(level: SecurityLevel) -> str:
        """Convert security level to severity string"""
        if level == SecurityLevel.CRITICAL:
            return "critical"
        elif level == SecurityLevel.HIGH_RISK:
            return "high"
        elif level == SecurityLevel.MEDIUM_RISK:
            return "medium"
        elif level == SecurityLevel.LOW_RISK:
            return "low"
        else:
            return "info"
