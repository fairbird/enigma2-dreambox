#ifndef __lib_base_io_h__
#define __lib_base_io_h__

#include <endian.h>
#include <string>

/**
 * Wrapper for low level I/O functions.
 */

class eIO
{
public:
	/**
	 * Wrapper for read(3), which guarantees to return either count or -1.
	 *
	 * @param fd file descriptor
	 * @param buf destination data buffer
	 * @param count number of bytes to read
	 * @param timeout maximum number of milliseconds to wait for completion
	 * @return count or -1
	 */
	static ssize_t read(int fd, void *buf, size_t count, int timeout = -1);

	/**
	 * Wrapper for write(3), which guarantees to return either count or -1.
	 *
	 * @param fd file descriptor
	 * @param buf source data buffer
	 * @param count number of bytes to read
	 * @return count or -1
	 */
	static ssize_t write(int fd, const void *buf, size_t count);

	/* this is needed to prevent bus errors caused by unaligned memory accesses on ARM >v6 */
	struct unaligned_uint64_t { uint64_t val; }  __attribute__ ((packed));
	struct unaligned_uint32_t { uint32_t val; } __attribute__ ((packed));

	static inline uint16_t be16(const void *p)
	{
		return be16toh(*(uint16_t *)p);
	}
	static inline uint32_t be24(const void *p)
	{
		const uint8_t *p8 = static_cast<const uint8_t *>(p);
		return (p8[0] << 16) | be16(&p8[1]);
	}
	static inline uint32_t be32(const void *p)
	{
		const unaligned_uint32_t *p32 = static_cast<const unaligned_uint32_t *>(p);
		return be32toh(p32->val);
	}
	static inline uint64_t be64(const void *p)
	{
		const unaligned_uint64_t *p64 = static_cast<const unaligned_uint64_t *>(p);
		return be64toh(p64->val);
	}
	static inline uint16_t le16(const void *p)
	{
		return le16toh(*(uint16_t *)p);
	}
	static inline uint32_t le24(const void *p)
	{
		const uint8_t *p8 = static_cast<const uint8_t *>(p);
		return le16(&p8[0]) | (p8[2] << 16);
	}
	static inline uint32_t le32(const void *p)
	{
		const unaligned_uint32_t *p32 = static_cast<const unaligned_uint32_t *>(p);
		return le32toh(p32->val);
	}
	static inline uint64_t le64(const void *p)
	{
		const unaligned_uint64_t *p64 = static_cast<const unaligned_uint64_t *>(p);
		return le64toh(p64->val);
	}
};

/**
 * Abstract interface for file readers.
 *
 * In addition to the pure virtual methods, every subclass shall implement
 * at least these three methods, where T shall be a resource identifier:
 *
 * - Constructor()
 * - Constructor(T)
 * - bool open(T)
 */

class iFileReader
{
public:
	iFileReader() :
		m_size(0)
	{
	}

	virtual ~iFileReader()
	{
	}

	/**
	 * Close the FileReader.
	 *
	 * Automatically called by the destructor. Must be called before
	 * open() is called a second time. Can be called to release the
	 * resource before the object is destroyed.
	 */
	virtual void close() = 0;

	/**
	 * Read data from the underlying resource.
	 *
	 * @return true on success
	 */
	virtual bool read() = 0;

	/**
	 * Indicates validity of the data after read().
	 *
	 * @return true if the data from the underlying resource which
	 *         has been read by the last call to read() is valid.
	 */
	virtual bool valid() const = 0;

	/**
	 * Number of bytes available after read().
	 *
	 * @return the size in bytes of the data read by the last
	 *         call to read().
	 */
	virtual size_t size() const { return m_size; }

protected:
	size_t m_size;
};

/**
 * Read binary files. Tries memory-mapped file I/O first with a fallback to
 * direct read operations, in which case it reads the complete file at once.
 */
class eBinaryReader : public iFileReader
{
public:
	/**
	 * Creates an instance of eBinaryReader.
	 */
	eBinaryReader();

	/**
	 * Creates an instance of eBinaryReader.
	 *
	 * @param filename name of the file to pass to open()
	 */
	eBinaryReader(const std::string &filename);
	virtual ~eBinaryReader();

	/**
	 * Opens a file for reading.
	 *
	 * @param filename name of the binary file to read
	 * @return true if the file could be opened
	 */
	virtual bool open(const std::string &filename);
	virtual void close();
	virtual bool read();
	virtual bool valid() const;

	/**
	 * Returns the data obtained by a call to read(). The pointer remains
	 * valid until the reader instance gets destroyed.
	 *
	 * @return a pointer to the data previously read.
	 */
	unsigned char *data() const { return (unsigned char *)m_data; }
	/**
	 * Same as data(), but returns a const pointer.
	 *
	 * @return a const pointer to the data previously read.
	 */
	const unsigned char *constData() const { return (const unsigned char *)m_data; }

protected:
	enum mode {
		NONE,
		MMAP,
		READ,
	};

	void *m_data;
	int m_file;
	char *m_filename;
	enum mode m_mode;

	virtual bool malloc();
	virtual bool mmap();
};

/**
 * Abstract interface for text file readers. Reads input data line by line.
 */
class iTextStreamReader : public iFileReader
{
public:
	enum cr_mode {
		KEEP,	/**< Don't modify the input. */
		STRIP,	/**< Strip carriage return and linefeed characters. */
	};

	/**
	 * @param mode how to handle CR/LF characters
	 */
	iTextStreamReader(enum cr_mode mode = STRIP);

	virtual ~iTextStreamReader();

	/**
	 * Read data from the underlying text resource, until either
	 * end-of-file occurs or CR/LF characters have been read.
	 *
	 * @return true on success
	 */
	virtual bool read();
	virtual bool valid() const;

	/**
	 * Returns the data obtained by a call to read(). The pointer remains
	 * valid until the reader instance gets destroyed.
	 *
	 * @return a pointer to the data previously read or NULL
	 */
	const char *data() const { return m_data; }

	/**
	 * Reads the next line of the underlying text resource and returns
	 * a pointer to the line or . Equal to calling read() followd by data().
	 *
	 * @return a pointer to the next line of text or NULL
	 */
	const char *nextData() { return read() ? data() : 0; }

protected:
	char *m_data;
	FILE *m_file;
	enum cr_mode m_mode;
	size_t m_n;
};

/**
 * Read text from an executed command through a pipe using direct read.
 * Reads the input pipe line by line.
 */
class eTextPipeReader : public iTextStreamReader
{
public:
	eTextPipeReader(enum cr_mode mode = STRIP);
	eTextPipeReader(const std::string &command, enum cr_mode mode = STRIP);
	virtual ~eTextPipeReader();

	/**
	 * Opens the input pipe to be used by the reader.
	 *
	 * @param command command line to execute and to read the output from
	 * @return true if the pipe could be created
	 */
	virtual bool open(const std::string &command);
	virtual void close();

protected:
	char *m_command;

	bool popen();
};

/**
 * Read text from files. Tries memory-mapped file I/O first and falls back to
 * direct read. Reads an input file line by line.
 */
class eTextFileReader : public iTextStreamReader
{
public:
	eTextFileReader(enum cr_mode mode = STRIP);
	eTextFileReader(const std::string &filename, enum cr_mode = STRIP);
	virtual ~eTextFileReader();

	/**
	 * Opens the specified input file to be used by the reader.
	 *
	 * @param filename location of the input file
	 * @return true if the file could be opened
	 */
	virtual bool open(const std::string &filename);
	virtual void close();

protected:
	char *m_filename;

	bool fopen(const char *mode);
};

/**
 * Interface template to read different types of numbers from a file.
 * Expects one number per line.
 */
template <typename T, T T_MIN, T T_MAX, T (*T_CONVERT)(const char *nptr, char **endptr, int base)>
class iNumberReader : public eTextFileReader
{
public:
	/**
	 * @param base the base to use when converting from text to a number (0 = auto)
	 */
	iNumberReader(int base = 0) :
		eTextFileReader(STRIP),
		m_base(base),
		m_data(0)
	{
	}

	/**
	 * @param filename name of the text file to read
	 * @param base the base to use when converting from text to a number (0 = auto)
	 */
	iNumberReader(const std::string &filename, int base = 0) :
		eTextFileReader(filename, STRIP),
		m_base(base),
		m_data(0)
	{
	}

	virtual ~iNumberReader()
	{
	}

	virtual bool read()
	{
		if (!eTextFileReader::read())
			return false;

		const char *str = eTextFileReader::data();
		char *end = 0;
		errno = 0;
		m_data = T_CONVERT(str, &end, m_base);

		/* strange test, but from the manual page */
		return ((errno != ERANGE || (m_data != T_MIN && m_data != T_MAX)) &&
			(errno == 0 || m_data != 0) &&
			(str != end));
	}

	T data() const { return m_data; }

private:
	int m_base;
	T m_data;
};

/**
 * Reads signed longs from text files.
 */
class eLongReader : public iNumberReader<long, LONG_MIN, LONG_MAX, strtol>
{
public:
	eLongReader(int base = 0) :
		iNumberReader<long, LONG_MIN, LONG_MAX, strtol>(base)
	{
	}

	eLongReader(const std::string &filename, int base = 0) :
		iNumberReader<long, LONG_MIN, LONG_MAX, strtol>(filename, base)
	{
	}

	virtual ~eLongReader()
	{
	}
};

/**
 * Reads unsigned longs from text files.
 */
class eUnsignedLongReader : public iNumberReader<unsigned long, ULONG_MAX, ULONG_MAX, strtoul>
{
public:
	eUnsignedLongReader(int base = 0) :
		iNumberReader<unsigned long, ULONG_MAX, ULONG_MAX, strtoul>(base)
	{
	}

	eUnsignedLongReader(const std::string &filename, int base = 0) :
		iNumberReader<unsigned long, ULONG_MAX, ULONG_MAX, strtoul>(filename, base)
	{
	}

	virtual ~eUnsignedLongReader()
	{
	}
};

#endif
