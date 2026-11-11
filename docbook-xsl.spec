Name:		docbook-xsl
Version:	1.75.2
Release:	1
Summary:	DocBook XSL stylesheets used by Gradle's documentation build
Group:		Development/Java
License:	MIT
URL:		https://docbook.sourceforge.net/projects/xsl/
# SourceForge docbook-xsl 1.75.2. The extension jars saxon65.jar and
# xalan27.jar are removed from this archive; they are prebuilt binaries.
Source0:	docbook-xsl-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	xalan-j2

%description
DocBook XSL 1.75.2 stylesheets. Gradle 9.9.1's build catalog names
net.sf.docbook:docbook-xsl at this version. The documentation task
unpacks that artifact and expects entries whose paths start with
docbook/. This package builds that layout into a jar from the
stylesheet sources. The two extension jars that came in the upstream
tarball are not included.

%prep
%autosetup -n docbook-xsl-%{version}
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print -delete
if find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) | grep -q .; then
	echo 'prebuilt binaries remain' >&2
	exit 1
fi
if find . -type d -name '*.jar' | grep -q .; then
	echo 'jar directories remain' >&2
	exit 1
fi

%build
set -eo pipefail
STAGE="%{_builddir}/dbstage"
rm -rf "$STAGE"
mkdir -p "$STAGE/docbook"
find . -mindepth 1 -maxdepth 1 -exec /bin/cp -a {} "$STAGE/docbook/" \;
test -f "$STAGE/docbook/xhtml/docbook.xsl"
test -f "$STAGE/docbook/common/l10n.xml"
test -f "$STAGE/docbook/COPYING"
jar cf docbook-xsl.jar -C "$STAGE" docbook
jar i docbook-xsl.jar
jar tf docbook-xsl.jar > jar.list
grep -F -q 'docbook/xhtml/docbook.xsl' jar.list
grep -F -q 'docbook/common/l10n.xml' jar.list
if grep -E '\.(class|jar)$' jar.list; then
	echo 'jar contains binaries' >&2
	exit 1
fi

cat > docbook-xsl.pom << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>net.sf.docbook</groupId>
  <artifactId>docbook-xsl</artifactId>
  <version>%{version}</version>
  <name>docbook-xsl</name>
  <description>DocBook XSL stylesheets</description>
  <licenses>
    <license>
      <name>MIT</name>
    </license>
  </licenses>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact docbook-xsl.pom:docbook-xsl.jar \
	--file-name docbook-xsl \
	--filelist .mfiles

%check
set -eo pipefail
# JDK XSLTC throws a null pointer in l10n.language on document('').
# Interpretive Xalan runs these stylesheets. The locale file is one
# large entity tree, so the JDK entity-size limit has to be turned off
# or the title text is dropped. The article has no document type, so
# this does not fetch a DTD.
WORKDIR="$(pwd)/docbook-check"
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR/classes" "$WORKDIR/xsl"
JAR=%{buildroot}%{_javadir}/docbook-xsl.jar
test -f "$JAR"
( cd "$WORKDIR/xsl" && jar xf "$JAR" )
test -f "$WORKDIR/xsl/docbook/xhtml/docbook.xsl"
cat > "$WORKDIR/article.xml" << 'EOF'
<?xml version="1.0"?>
<article>
  <title>gradle</title>
  <para>docbook_ok</para>
</article>
EOF
cat > "$WORKDIR/Smoke.java" << 'EOF'
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.stream.StreamResult;
import javax.xml.transform.stream.StreamSource;

public class Smoke {
	public static void main(String[] args) throws Exception {
		String xsl = args[0];
		String xml = Files.readString(Path.of(args[1]));
		TransformerFactory tf = TransformerFactory.newInstance(
			"org.apache.xalan.processor.TransformerFactoryImpl",
			Thread.currentThread().getContextClassLoader());
		Transformer t = tf.newTransformer(new StreamSource(Path.of(xsl).toUri().toString()));
		StringWriter out = new StringWriter();
		t.transform(new StreamSource(new StringReader(xml)), new StreamResult(out));
		String html = out.toString();
		if (!html.contains("gradle") || !html.contains("docbook_ok") || !html.contains("DocBook XSL Stylesheets V1.75.2")) {
			System.err.println(html.substring(0, Math.min(html.length(), 1500)));
			throw new RuntimeException("bad html");
		}
		System.out.println("docbook_ok gradle 1.75.2");
	}
}
EOF
javac --release 11 -encoding UTF-8 -cp "%{_javadir}/xalan.jar:%{_javadir}/serializer.jar" -d "$WORKDIR/classes" "$WORKDIR/Smoke.java"
java \
	-Djdk.xml.totalEntitySizeLimit=0 \
	-Djdk.xml.maxGeneralEntitySizeLimit=0 \
	-Djdk.xml.entityExpansionLimit=0 \
	-Djdk.xml.maxParameterEntitySizeLimit=0 \
	-Djdk.xml.entityReplacementLimit=0 \
	-cp "$WORKDIR/classes:%{_javadir}/xalan.jar:%{_javadir}/serializer.jar" \
	Smoke \
	"$WORKDIR/xsl/docbook/xhtml/docbook.xsl" \
	"$WORKDIR/article.xml" > "$WORKDIR/out.txt"
cat "$WORKDIR/out.txt"
grep -F -q 'docbook_ok gradle 1.75.2' "$WORKDIR/out.txt"

%files -f .mfiles
%license COPYING
