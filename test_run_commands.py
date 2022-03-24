from run_commands import (
    GRADLE_BUILD_REGEX,
    JAVAC_BUILD_REGEX,
    JS_BUILD_REGEX,
    MAKE_BUILD_REGEX,
    MAVEN_BUILD_REGEX,
    PYTHON_BUILD_REGEX,
    RUBY_BUILD_REGEX,
    match_cmd_regex
)

VALID = 'valid'
INVALID = 'invalid'

TESTS = {
    VALID: {
        JS_BUILD_REGEX: [
            'npm install',
            'npm install --arg',
            '/mypath/npm install --arg'
            'npm ci',
            './npm ci',
            'npm ci --ignore-scripts --no-audit --no-progress --prefer-offline',
            'npm test',
            'npm run build',
            'npm run ci',
            'npm run test'
        ],
        GRADLE_BUILD_REGEX: [
            'gradle build',
            './gradlew clean build  -x test publishPlugins',
            'gradle test'
        ],
        MAVEN_BUILD_REGEX: [
            'mvn clean install',
            '/mypath/mvn install',
            'mvn -s .m2/settings.xml -gs .m2/settings.xml -B package',
            'mvn -B package --file pom.xml',
            'mvn -B clean install -T2 -Prelease --file mypath/pom.xml -Dspotless.apply.skip=true',
            'mvn -V -B -U --no-transfer-progress clean verify -DskipITs=false',
            'mvn test',
            'mvn compile'
        ],
        MAKE_BUILD_REGEX: [
            'cmake',
            'make',
            '/mypath/make',
            'mypath/cmake',
            'make --arg',
            ' cmake --build . --config $BUILD_TYPE',
            'blah cmake -S fltk -B fltk/build blah',
            'cmake -E make_directory ${{runner.workspace}}/build'
        ],
        JAVAC_BUILD_REGEX: [
            'javac',
            './javac --arg'
        ],
        RUBY_BUILD_REGEX: [
            'rake',
            './path/rake',
            'rake arg',
            'bundle install',
            '../mypath/bundle install',
            './rake --args',
            'bundle exec rspec mypath/spec.rb',
            'bundle install --jobs 4 --retry 3'
        ],
        PYTHON_BUILD_REGEX: [
            'pip install pytest pytest-randomly pytest-cov'
            'pip install -r requirements.txt',
            'pip install --upgrade -r requirements.txt',
            'python -m venv venv',
            'python2 -c "from this import that; print(that)"',
            'python setup.py patch_version --platform=$Env:BUILD_NUMBER.$(git rev-parse --short HEAD)',
            'python3 setup.py test',
            'python3 -m pip install --upgrade pip setuptools wheel',
            'pytest --verbose test/mytest.py',
            '/mypath/pytest mypath/test'
        ]
    },
    INVALID: {
        JS_BUILD_REGEX: [
            'gpm install',
            'npm cia',
            'npms install',
            'npm finstall',
            'npm run random',
            'npm run install'
        ],
        GRADLE_BUILD_REGEX: [
            'dgradle build',
            './gradlef clean build',
            'gradles build',
            'gradle tester',
            'gradle debuild',
        ],
        MAVEN_BUILD_REGEX: [
            'maven',
            'dmvn',
            'mvnz',
            'mvn random',
            'mvn dinstall',
            'mvn installf'
        ],
        MAKE_BUILD_REGEX: [
            'cmaker',
            'dmake'
        ],
        JAVAC_BUILD_REGEX: [
            './myjavac',
            'javacc',
            'djavac'
        ],
        RUBY_BUILD_REGEX: [
            'raker',
            'drake',
            'bundle dinstall',
            'dbundle install'
            'bundle installer',
            'bunlder install'
        ],
        PYTHON_BUILD_REGEX: [
            'pipd install',
            'dpip install',
            'pip dinstall',
            'pip installer',
            'python4',
            'apython',
            'pytesta',
            'apytest'
        ]
    }
}


def run_tests():
    print('Running tests for run_commands...')
    num_failed = 0
    for validity in [VALID, INVALID]:
        should_be_match = True if validity == VALID else False
        for regexp, test_cmds in TESTS[validity].items():
            for cmd in test_cmds:
                is_match = match_cmd_regex(regexp, cmd)
                if is_match != should_be_match:
                    print(f"Should be {validity}: {cmd}")
                    num_failed += 1

    if num_failed == 0:
        print('Test summary: All tests passed!')
    else:
        print(f"Test summary: {num_failed} tests failed!")


if __name__ == "__main__":
    run_tests()
